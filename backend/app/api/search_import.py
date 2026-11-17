import logging
import re

import requests
from app.services.music_theory import SongModel, parse_ultimate_guitar_html
from app.services.scraper import SongImportError, has_lyrics, import_from_url
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


def fetch_song_page(url: str) -> SongModel:
    if "ultimate-guitar" not in url:
        return import_from_url(url)
    try:
        html = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}).text
        song = parse_ultimate_guitar_html(html)
    except Exception as e:
        logger.error(f"Failed to fetch song page {url}: {e}")
        song = None
    if song is None:
        raise SongImportError("Failed to fetch song from URL")
    if not has_lyrics(song):
        raise SongImportError("No song text found at that URL.")
    return song


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
    try:
        song = fetch_song_page(url)
    except SongImportError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "title": song.title,
        "artist": song.artist,
        "capo": song.capo,
        "key": song.key,
        "body": str(song),
        "imported_from": url,
    }
