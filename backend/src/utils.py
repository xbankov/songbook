import logging
import traceback

import requests
from model.song import Song

logger = logging.getLogger(__name__)


def download_url(url):
    with requests.get(url) as response:
        response.raise_for_status()
        return response.text


def download(url):
    supported_urls = ["ultimate-guitar", "supermusic.cz"]
    if "ultimate-guitar" in url:
        logger.info(f"Processing url as ultimate-guitar: {url}")
        return download_ultimate_guitar(url)
    else:
        raise NotImplementedError(
            f"This url is not supported yet: {url}. Supported: {supported_urls}"
        )


def download_ultimate_guitar(url) -> Song:
    try:
        html = download_url(url)
    except requests.RequestException as e:
        logger.error(f"Requested URL {url} cannot be retrieved: {e}")
        logger.error(traceback.format_exc())
        return False

    return Song.from_ug_html(html)


# Use exported firefox bookmarks!
# def parse_firefox_bookmars():
#     with open("FIREFOX_BOOKMARKS_FILE_PATH", "r") as fp:
#         bookmarks = json.load(fp)
#         toolbar = bookmarks["children"][1]
#         music = [
#             folder for folder in toolbar["children"] if folder["title"] == "Music"
#         ][0]


# def extract_recursive(item):
#     if item["type"] == "text/x-moz-place-separator":
#         return []

#     elif item["type"] == "text/x-moz-place":
#         entry = BookmarkEntry(item["title"], item["uri"])
#         return [entry]

#     elif item["type"] == "text/x-moz-place-container":
#         return [uri for child in item["children"] for uri in extract_recursive(child)]
