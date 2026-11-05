from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.song import Song
from app.schemas.song import SongOut

router = APIRouter(prefix="/api/artists", tags=["artists"])


@router.get("")
async def list_artists(
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    query = select(Song.artist, func.count(Song.id).label("song_count"))
    if search:
        query = query.where(Song.artist.ilike(f"%{search}%"))
    query = query.group_by(Song.artist).order_by(func.count(Song.id).desc()).limit(limit)
    result = await db.execute(query)
    return [{"artist": row[0], "song_count": row[1]} for row in result.all()]


@router.get("/{artist_name}/songs", response_model=list[SongOut])
async def get_artist_songs(
    artist_name: str,
    sort: str = Query("title"),
    order: str = Query("asc"),
    db: AsyncSession = Depends(get_db),
):
    query = select(Song).where(Song.artist.ilike(artist_name))
    sort_col = getattr(Song, sort, Song.title)
    if order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())
    result = await db.execute(query)
    return result.scalars().all()
