from dataclasses import dataclass
from pathlib import Path
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
import config as config
import pdfkit
import shutil
from helpers import chordpro2html


@dataclass
class SongEntry:
    title: str
    artist: str
    path: str


def get_song_entry(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    soup = BeautifulSoup(content, "html.parser")
    title, artist = soup.find("h1", {"id": "title"}).get_text(strip=True).split("-")
    title = title.strip()
    artist = artist.strip()
    return SongEntry(title=title, artist=artist, path=path)


def main():
    config.init_dirs()
    print("#####################################################")
    print("######### CONVERT CHORDPRO TO HTML ##################")
    print("#####################################################")
    chordpro2html(config.MANUAL_NORMALIZED_DIR, config.HTML_DIR)

    print("#####################################################")
    print("######### CONVERT HTML TO PDF #######################")
    print("#####################################################")

    songs = [
        get_song_entry(e)
        for e in config.HTML_DIR.iterdir()
    ]

    env = Environment(loader=FileSystemLoader(str(config.ROOT_DIR)))
    book_template = env.get_template(config.TEMPLATE_BOOK)

    def sorting_key(song):
        return song.artist, song.title

    sorted_paths = [str(Path(*song.path.parts[len(config.ROOT_DIR.parts):])) for song in sorted(songs, key=sorting_key)]
    book_content = book_template.render(songs=sorted_paths)

    html_file_path = config.FINAL_OUTPUT_DIRECTORY / "songbook.html"
    pdf_file_path = config.FINAL_OUTPUT_DIRECTORY / "songbook.pdf"

    with open(html_file_path, "w", encoding="utf-8") as f:
        f.write(book_content)

    shutil.copyfile(config.TEMPLATE_STYLE, config.FINAL_OUTPUT_DIRECTORY / config.TEMPLATE_STYLE.name)

    configuration = pdfkit.configuration(wkhtmltopdf=config.WKHTMLTOPDF)
    options = {
        "--enable-local-file-access": "",
    }

    pdfkit.from_file(
        str(html_file_path),
        str(pdf_file_path),
        css=config.TEMPLATE_STYLE,
        configuration=configuration,
        toc={
            "toc-header-text": "Table of Contents",
            
        },
        options=options,
    )


if __name__ == "__main__":
    main()
