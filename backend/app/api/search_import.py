import logging
import re

import requests
from app.services.music_theory import SongModel, parse_ultimate_guitar_html
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])

SEARCH_SOURCES = [
    {
        "name": "ultimate-guitar",
        "url": "https://www.ultimate-guitar.com/search.php",
        "params": {"search_type": "title", "value": ""},
        "parser": "ug_search",
    },
]


def search_ultimate_guitar(query: str) -> list[dict]:
    results = []
    try:
        url = f"https://www.ultimate-guitar.com/search.php?search_type=title&value={requests.utils.quote(query)}"
        html = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}).text
        soup = BeautifulSoup(html, "lxml")
        store = soup.find("div", {"class": "js-store"})
        if store:
            import json

            data = json.loads(store["data-content"])
            tabs = (
                data.get("store", {}).get("page", {}).get("data", {}).get("results", [])
            )
            for tab in tabs[:10]:
                tab_url = tab.get("tab_url", "")
                results.append(
                    {
                        "title": tab.get("song_name", "Unknown"),
                        "artist": tab.get("artist_name", "Unknown"),
                        "url": tab_url,
                        "source": "ultimate-guitar",
                        "type": tab.get("type", ""),
                        "rating": tab.get("rating", 0),
                        "votes": tab.get("votes", 0),
                    }
                )
    except Exception as e:
        logger.error(f"Ultimate Guitar search failed: {e}")
    return results


def fetch_song_page(url: str) -> SongModel | None:
    try:
        html = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}).text
        if "ultimate-guitar" in url:
            return parse_ultimate_guitar_html(html)
        else:
            soup = BeautifulSoup(html, "lxml")
            title_el = soup.select_one("h1")
            artist_el = soup.select_one("h2")
            body_el = soup.select_one(".chord-text, pre, .chord")
            if body_el:
                title = title_el.get_text(strip=True) if title_el else "Unknown"
                artist = artist_el.get_text(strip=True) if artist_el else "Unknown"
                body = body_el.get_text(strip=True)
                return SongModel.from_chordpro(body)
    except Exception as e:
        logger.error(f"Failed to fetch song page {url}: {e}")
    return None


@router.get("")
async def search_songs(
    q: str = Query(..., min_length=2),
    source: str = Query("all"),
):
    results = []
    if source in ("all", "ultimate-guitar"):
        results.extend(search_ultimate_guitar(q))
    return {"results": results, "query": q}


@router.post("/import")
async def import_searched_song(url: str = Query(...)):
    song = fetch_song_page(url)
    if song is None:
        raise HTTPException(status_code=400, detail="Failed to fetch song from URL")
    return {
        "title": song.title,
        "artist": song.artist,
        "capo": song.capo,
        "key": song.key,
        "body": str(song),
        "imported_from": url,
    }
