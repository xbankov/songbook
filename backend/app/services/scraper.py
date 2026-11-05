import logging
import re

import requests
from app.services.music_theory import SongModel, parse_ultimate_guitar_html
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def fetch_url(url: str) -> str:
    with requests.get(url, timeout=30) as resp:
        resp.raise_for_status()
        return resp.text


def scrape_ultimate_guitar(url: str) -> SongModel | None:
    try:
        html = fetch_url(url)
        return parse_ultimate_guitar_html(html)
    except Exception as e:
        logger.error(f"Failed to scrape Ultimate Guitar URL: {url}: {e}")
        return None


def scrape_supermusic(url: str) -> SongModel | None:
    try:
        html = fetch_url(url)
        soup = BeautifulSoup(html, "lxml")
        title_el = soup.select_one("h1")
        artist_el = soup.select_one("h2")
        body_el = soup.select_one(".chord-text, pre, .chord")
        title = title_el.get_text(strip=True) if title_el else "Unknown"
        artist = artist_el.get_text(strip=True) if artist_el else "Unknown"
        body = body_el.get_text(strip=True) if body_el else ""
        return SongModel.from_chordpro(body)
    except Exception as e:
        logger.error(f"Failed to scrape supermusic URL: {url}: {e}")
        return None


def detect_source(url: str) -> str:
    if "ultimate-guitar" in url:
        return "ultimate-guitar"
    elif "supermusic" in url:
        return "supermusic"
    return "unknown"


def import_from_url(url: str) -> SongModel | None:
    source = detect_source(url)
    if source == "ultimate-guitar":
        return scrape_ultimate_guitar(url)
    elif source == "supermusic":
        return scrape_supermusic(url)
    else:
        logger.warning(f"Unsupported URL: {url}")
        return None
