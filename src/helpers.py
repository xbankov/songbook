import json
import re
from time import sleep
from dataclasses import dataclass
import traceback
from bs4 import BeautifulSoup
import pandas as pd
import requests
import config
from tqdm import tqdm


@dataclass
class SongEntry:
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
    return config.RAW_DIR / f"{uri.replace('/', '+')}.html"


def get_norm_filename(uri):
    return config.NORMALIZED_DIR / f"{uri.replace('/', '+')}.txt"


def normalize_ultimate_guitar(tab, title):
    norm_tab = []
    norm_tab.append(f"{{title: {title}}}")

    capo_match = re.search(r"Capo: (\d+)", tab)
    capo = int(capo_match.group(1)) if capo_match else None
    if capo:
        norm_tab.append(f"{{capo: {capo}}}")

    sections = tab.split("\r\n\r\n")
    for section in sections:
        lines = [l for l in section.split("\r\n") if len(l) != 0]
        if len(lines) == 0:
            continue

        norm_tab.append(lines[0])
        if len(lines) == 1:
            continue
        norm_lines = []
        i = 1
        while i < len(lines):
            current_line = lines[i]

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
                norm_lines.append(lines[i])
                i += 1

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
        except KeyError as e:
            print(e)
            print(
                f"Not recognized tabs for file: {str(raw_filename).replace('+', '/')}"
            )
            traceback.print_exc()
            tab = ""
        title = get_ug_title(raw_filename)
        tab = normalize_ultimate_guitar(tab, title)

    elif "supermusic" in str(raw_filename):
        tab = ""
    else:
        print(f"Not recognized format: {raw_filename}")
        tab = ""

    save_text(tab, norm_filename)


def normalize(csv_file_path):
    data = pd.read_csv(csv_file_path, index_col=False)

    for _, row in tqdm(data.iterrows(), total=len(data)):
        raw_filename = get_raw_filename(row.uri)
        norm_filename = get_norm_filename(row.uri)
        if norm_filename.exists() and not config.FORCE["NORMALIZE"]:
            continue
        normalize_txt(raw_filename, norm_filename)


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


class SongEntry:
    def __init__(self, title, uri):
        self.title = title
        self.uri = uri


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
        entry = SongEntry(item["title"], item["uri"])
        return [entry]

    elif item["type"] == "text/x-moz-place-container":
        return [uri for child in item["children"] for uri in extract_recursive(child)]
