import logging

from app.services import ultimate_guitar
from app.services.scraper import SongImportError, import_from_url
from fastapi import APIRouter, HTTPException, Query
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
async def search_songs(
    q: str = Query(..., min_length=2),
    source: str = Query("all"),
):
    results = []
    if source in ("all", "ultimate-guitar"):
        try:
            results.extend(await run_in_threadpool(ultimate_guitar.search, q))
        except ultimate_guitar.UltimateGuitarError as e:
            logger.error(f"Ultimate Guitar search failed: {e}")
    return {"results": results, "query": q}


@router.post("/import")
async def import_searched_song(url: str = Query(...)):
    """Preview a song without saving it; same importer as POST /api/songs/import."""
    try:
        song = await run_in_threadpool(import_from_url, url)
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
