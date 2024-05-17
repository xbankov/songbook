from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.resolve()
DATA_DIR = ROOT_DIR / "data"
FIREFOX_BOOKMARKS_FILE_PATH = DATA_DIR / "src/bookmarks-2024-02-18.json"
CSV_FILE_PATH = DATA_DIR / "src/bookmarks-2024-02-18.csv"
RAW_DIR = DATA_DIR / "raw"
NORMALIZED_DIR = DATA_DIR / "normalized"
MANUAL_NORMALIZED_DIR = DATA_DIR / "after_manual_correction"
HTML_DIR = DATA_DIR / "html"
PDF_DIR = DATA_DIR / "pdf"
FINAL_OUTPUT_DIRECTORY = DATA_DIR / "output"


def init_dirs():
    DATA_DIR.mkdir(exist_ok=True, parents=True)
    RAW_DIR.mkdir(exist_ok=True, parents=True)
    NORMALIZED_DIR.mkdir(exist_ok=True, parents=True)
    MANUAL_NORMALIZED_DIR.mkdir(exist_ok=True, parents=True)
    HTML_DIR.mkdir(exist_ok=True, parents=True)
    PDF_DIR.mkdir(exist_ok=True, parents=True)
    FINAL_OUTPUT_DIRECTORY.mkdir(exist_ok=True, parents=True)


TEMPLATE_BOOK = "src/static/book_template.html"
TEMPLATE_SONG = "src/static/song_template.html"
TEMPLATE_STYLE = ROOT_DIR / "src/static/styles.css"

FORCE = {
    "PARSE": False,
    "DOWNLOAD": False,
    "NORMALIZE": False,
}
SLEEP = 2
SUPPORTED = ["supermusic", "ultimate-guitar"]
WKHTMLTOPDF = "/usr/local/bin/wkhtmltopdf"
