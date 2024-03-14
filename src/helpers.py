import json
import re
from sqlite3 import NotSupportedError
from time import sleep
from dataclasses import dataclass
from sqlite3 import NotSupportedError
from time import sleep
import traceback

import pandas as pd
import pdfkit
import requests
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from tqdm import tqdm

import config


@dataclass
class BookmarkEntry:
    title: str
    uri: str


def download_url(url, filename):
    with requests.get(url) as response:
        if response.ok:
            html_output = response.text
            save_text(html_output, filename)
        else:
            print(f"ERROR: {response.status_code}")


def save_text(text, filename):
    with open(filename, "w", encoding="utf-8") as file:
        file.write(text)


def load_text(filename):
    with open(filename, "r", encoding="utf-8") as file:
        return file.read()


def get_raw_filename(uri):
    filename = uri.replace("https://", "").replace("/", "&")
    return config.RAW_DIR / f"{filename}.html"


def get_norm_filename(uri):
    filename = uri.replace("https://", "").replace("/", "&")
    return config.NORMALIZED_DIR / f"{filename}.txt"


def extract(music_folder, csv_path):
    if not csv_path.exists() or config.FORCE["PARSE"]:
        songs = extract_recursive(music_folder)
        songs_dict_list = [
            {"title": song.title, "uri": song.uri, "status": "Not Downloaded"}
            for song in songs
            if any(website in song.uri for website in config.SUPPORTED)
        ]
        data = pd.DataFrame(songs_dict_list)
        data.to_csv(csv_path, index=False)


def extract_recursive(item):
    if item["type"] == "text/x-moz-place-separator":
        return []

    elif item["type"] == "text/x-moz-place":
        entry = BookmarkEntry(item["title"], item["uri"])
        return [entry]

    elif item["type"] == "text/x-moz-place-container":
        return [uri for child in item["children"] for uri in extract_recursive(child)]


def download(csv_file_path):
    data = pd.read_csv(csv_file_path, index_col=False)

    for idx, row in tqdm(data.iterrows(), total=len(data)):
        raw_filename = get_raw_filename(row.uri)
        if raw_filename.exists() and not config.FORCE["DOWNLOAD"]:
            data.at[idx, "status"] = "Downloaded"
            continue
        try:
            download_url(row.uri, raw_filename)
            data.to_csv(csv_file_path, index=False)
            sleep(config.SLEEP)
            data.at[idx, "status"] = "Downloaded"
        except Exception as e:
            print(e)
    data.to_csv(csv_file_path, index=False)


def normalize(csv_file_path):
    data = pd.read_csv(csv_file_path, index_col=False)

    for _, row in tqdm(data.iterrows(), total=len(data)):
        raw_filename = get_raw_filename(row.uri)
        norm_filename = get_norm_filename(row.uri)
        if norm_filename.exists() and not config.FORCE["NORMALIZE"]:
            continue
        normalize_txt(raw_filename, norm_filename)


def normalize_ultimate_guitar(tab, title, artist):
    norm_tab = []
    norm_tab.append(f"{{title: {title}}}")
    norm_tab.append(f"{{artist: {artist}}}")
    capo_match = re.search(r"[cC]apo:? (.+)", tab)
    if capo_match:
        norm_tab.append(f"{{capo: {capo_match.group(1)}}}")

    sections = tab.split("\r\n\r\n")
    for section in sections:
        norm_lines = []
        lines = [l for l in section.split("\r\n") if len(l) != 0]
        if len(lines) == 0:
            continue

        i = 0
        start_tag = ""
        end_tag = ""
        while i < len(lines):
            current_line = lines[i]

            if i == 0 and current_line.startswith("[") and current_line.endswith("]"):
                section_title = current_line[1:-1]
                if "intro" in section_title.lower():
                    start_tag = "{start_of_verse: Intro}"
                    end_tag = "{end_of_verse}"

                elif "verse" in section_title.lower():
                    start_tag = "{start_of_verse}"
                    end_tag = "{end_of_verse}"

                elif "chorus" in section_title.lower():
                    start_tag = "{start_of_chorus}"
                    end_tag = "{end_of_chorus}"

                elif "bridge" in section_title.lower():
                    start_tag = "{start_of_bridge}"
                    end_tag = "{end_of_bridge}"

                elif "outro" in section_title.lower():
                    # TODO - specify value and process it in html rendering
                    start_tag = "{start_of_verse: Outro}"
                    end_tag = "{end_of_verse}"

                else:
                    print(f"Unknown starting tag: {current_line}. Skipping ...")

                if start_tag:
                    norm_lines.append(start_tag)

            if "[tab]" in current_line:
                next_line = lines[i + 1]
                current_line = current_line.replace("[tab]", "")
                next_line = next_line.replace("[/tab]", "")

                chords_positions = {}
                offset = 0
                for match in re.finditer(r"\[ch]([^\]]*)\[/ch]", current_line):
                    chord = match.group(1)
                    pos = match.start() - offset
                    offset += match.end() - match.start()
                    chords_positions[pos] = chord

                offset = 0
                for pos in sorted(chords_positions.keys()):
                    chord = f"[{chords_positions[pos]}]"
                    next_line = (
                        next_line[: pos + offset] + chord + next_line[pos + offset :]
                    )
                    offset += len(f"[{chord}]")
                norm_lines.append(next_line)
                i += 2

            elif "[ch]" in current_line:
                norm_chords = re.sub(r"\[ch]([^\]]*)\[/ch]", r"[\1]", current_line)
                norm_lines.append(norm_chords)
                i += 1
            else:
                i += 1
                # Skip
                # norm_lines.append(lines[i])

        if end_tag:
            norm_lines.append(end_tag)
        norm_tab.append("\n".join(norm_lines))

    return "\n\n".join(norm_tab)


def get_ug_title(raw_filename):
    name = str(raw_filename).split("+")[-1].split(".")[0].split("-")[:-1]
    name = " ".join(name).capitalize()
    name = name.replace("chords", "").strip()
    return name


def normalize_txt(raw_filename, norm_filename):
    html = load_text(raw_filename)
    if "ultimate-guitar" in str(raw_filename):
        soup = BeautifulSoup(html, "lxml")
        div = soup.find("div", {"class": "js-store"})
        json_string = div["data-content"]
        data = json.loads(json_string)
        try:
            tab = data["store"]["page"]["data"]["tab_view"]["wiki_tab"]["content"]
            title = data["store"]["page"]["data"]["tab_view"]["versions"][0][
                "song_name"
            ]
            artist = data["store"]["page"]["data"]["tab_view"]["versions"][0][
                "artist_name"
            ]
        except (KeyError, IndexError) as e:
            print(e)
            print(
                f"Not recognized tabs for file: {str(raw_filename).replace('+', '/')}"
            )
            traceback.print_exc()
            tab = ""
            title = ""
            artist = ""
        tab = normalize_ultimate_guitar(tab, title, artist)

    elif "supermusic" in str(raw_filename):
        tab = ""
    else:
        print(f"Not recognized format: {raw_filename}")
        tab = ""

    save_text(tab, norm_filename)


def chordpro2html(norm_dir, html_dir):
    for norm_file_path in norm_dir.iterdir():
        norm_text = load_text(norm_file_path)
        html_file_path = html_dir / f"{norm_file_path.stem}.html"

        env = Environment(loader=FileSystemLoader(str(config.ROOT_DIR)))
        song_template = env.get_template(str(config.TEMPLATE_SONG))

        title = None
        title_match = re.search(r"\{title: (.+)\}", norm_text)
        if title_match:
            title = title_match.group(1)
            norm_text = re.sub(r"\{title: (.+?)\}", "", norm_text).strip()
        else:
            raise NotSupportedError(
                f"ChordPro without title not supported: {norm_text}"
            )

        artist = None
        artist_match = re.search(r"\{artist: (.+)\}", norm_text)
        if artist_match:
            artist = artist_match.group(1)
            norm_text = re.sub(r"\{artist: (.+?)\}", "", norm_text).strip()
        else:
            raise NotSupportedError(
                f"ChordPro without artist not supported: {norm_text}"
            )

        capo_match = re.search(r"\{capo: (.+)\}", norm_text)
        capo = None
        if capo_match:
            capo = capo_match.group(1)
            norm_text = re.sub(r"\{capo: (.+?)\}", "", norm_text).strip()

        song_lines = [d.strip() for d in norm_text.split("\n") if len(d) != 0]
        song_rendered = song_template.render(
            title=title, artist=artist, capo=capo, content=song_lines
        )
        with open(html_file_path, "w") as output_file:
            output_file.write(song_rendered)


def html2pdf(html_dir, pdf_dir):
    configuration = pdfkit.configuration(wkhtmltopdf=config.WKHTMLTOPDF)
    options = {"--enable-local-file-access": ""}
    css = "src/static/styles.css"
    for html_file_path in html_dir.iterdir():
        pdf_file_path = pdf_dir / f"{html_file_path.stem}.pdf"
        pdfkit.from_file(
            str(html_file_path),
            str(pdf_file_path),
            css=css,
            configuration=configuration,
            options=options,
        )
