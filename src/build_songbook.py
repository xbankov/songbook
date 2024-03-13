from dataclasses import dataclass
from pathlib import Path

import pdfkit
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

import config as config
from helpers import chordpro2html


def main():
    
    print("#####################################################")
    print("######### CONVERT CHORDPRO TO HTML ##################")
    print("#####################################################")
    chordpro2html(config.MANUAL_NORMALIZED_DIR, config.HTML_DIR)

    print("#####################################################")
    print("######### CONVERT HTML TO PDF #######################")
    print("#####################################################")

    songs = [
        get_song_entry(str(Path(*e.parts[len(config.ROOT_DIR.parts) :])))
        for e in config.HTML_DIR.iterdir()
    ]

    def sorting_key(song):
        return (song.artist, song.title)

    sorted_paths = [song.path for song in sorted(songs, key=sorting_key)]

    env = Environment(loader=FileSystemLoader(str(config.ROOT_DIR)))
    book_template = env.get_template(config.TEMPLATE_BOOK)
    book_content = book_template.render(songs=sorted_paths)

    with open(config.FINAL_OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(book_content)

    configuration = pdfkit.configuration(wkhtmltopdf=str(config.WKHTMLTOPDF))
    options = {
        "--footer-center": "[page]",
        "--enable-local-file-access": "",
        "--outline-depth": 2,
    }
    pdfkit.from_file(
        str(config.FINAL_OUTPUT_HTML),
        str(config.FINAL_OUTPUT_PDF),
        css=config.TEMPLATE_STYLE,
        configuration=configuration,
        toc={
            "toc-header-text": "Table of Contents",
            # "xsl-style-sheet": str(config.WKHTMLTOPDF_XSL),
        },
        options=options,
    )


if __name__ == "__main__":
    main()
