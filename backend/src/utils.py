import logging
import traceback

import requests
from models.song import Song

logger = logging.getLogger(__name__)


def download_url(url):
    with requests.get(url, ) as response:
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


def download_ultimate_guitar(url) -> Song | None:
    try:
        html = download_url(url)
        return Song.from_ug_html(html)
    except requests.RequestException as e:
        logger.error(f"Requested URL {url} cannot be retrieved: {e}")
        logger.error(traceback.format_exc())
        return None


def get_logger(file):

    logging.basicConfig(
        level=logging.INFO,  # Set the log level to INFO
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Set the log format
        handlers=[logging.StreamHandler()],  # Add a handler that outputs to stdout
    )
    return logging.getLogger(file)
