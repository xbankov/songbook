import logging

import requests
from app.services.music_theory import SongModel, parse_ultimate_guitar_html
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SUPERMUSIC_BLOCKED = (
    "Supermusic blocks automatic import: its song pages need a browser check "
    "first. Open the song in your browser, copy the text, and paste it into a "
    "new song or Bulk import."
)


class SongImportError(Exception):
    """A URL could not be turned into a song; the message is shown to the user."""


def fetch_url(url: str) -> str:
    with requests.get(url, timeout=30) as resp:
        resp.raise_for_status()
        return resp.text


def is_supermusic_challenge(soup: BeautifulSoup) -> bool:
    """True for supermusic's anti-bot stub ("Načítavam...") instead of a song (#133)."""
    if soup.select_one('script[src*="/js/smc.js"]'):
        return True
    return soup.select_one("#msg[data-n][data-t]") is not None


def has_lyrics(song: SongModel) -> bool:
    return any(str(line).strip() for section in song.sections for line in section.lines)


def scrape_ultimate_guitar(url: str) -> SongModel | None:
    try:
        html = fetch_url(url)
        return parse_ultimate_guitar_html(html)
    except Exception as e:
        logger.error(f"Failed to scrape Ultimate Guitar URL: {url}: {e}")
        return None


def parse_supermusic_html(html: str) -> SongModel:
    soup = BeautifulSoup(html, "lxml")
    if is_supermusic_challenge(soup):
        raise SongImportError(SUPERMUSIC_BLOCKED)
    body_el = soup.select_one(".chord-text, pre, .chord")
    if body_el is None:
        raise SongImportError("No song text found on that supermusic page.")
    return SongModel.from_chordpro(body_el.get_text(strip=True))


def scrape_supermusic(url: str) -> SongModel:
    try:
        html = fetch_url(url)
    except requests.RequestException as e:
        logger.error(f"Failed to fetch supermusic URL: {url}: {e}")
        raise SongImportError("Could not download that supermusic page.") from e
    return parse_supermusic_html(html)


def detect_source(url: str) -> str:
    if "ultimate-guitar" in url:
        return "ultimate-guitar"
    elif "supermusic" in url:
        return "supermusic"
    return "unknown"


def import_from_url(url: str) -> SongModel:
    """Fetch and parse a song; raise SongImportError rather than return an empty song."""
    source = detect_source(url)
    if source == "ultimate-guitar":
        song = scrape_ultimate_guitar(url)
    elif source == "supermusic":
        song = scrape_supermusic(url)
    else:
        logger.warning(f"Unsupported URL: {url}")
        raise SongImportError(
            "Unsupported site: import works for Ultimate Guitar and supermusic URLs."
        )
    if song is None:
        raise SongImportError("Failed to import song from URL")
    if not has_lyrics(song):
        raise SongImportError("No song text found at that URL.")
    return song
