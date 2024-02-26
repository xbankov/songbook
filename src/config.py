from pathlib import Path

DATA_DIR = Path("data/")
FIREFOX_BOOKMARKS_FILE_PATH = DATA_DIR / "src/bookmarks-2024-02-18.json"
CSV_FILE_PATH = DATA_DIR / "src/bookmarks-2024-02-18.csv"
RAW_DIR = DATA_DIR / "raw"

NORMALIZED_DIR = DATA_DIR / "normalized"
FORCE = {
    "PARSE": False,
    "DOWNLOAD": False,
    "NORMALIZE": True,
}
SLEEP = 2
SUPPORTED = ["supermusic", "ultimate-guitar"]
