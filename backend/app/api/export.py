import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.settings import Settings
from app.models.song import Song
from app.models.songbook import Songbook, SongbookEntry
from app.services.music_theory import SongModel as ST
from app.services.pdf import generate_song_pdf, generate_songbook_pdf

router = APIRouter(prefix="/api/export", tags=["export"])


async def get_global_settings(db: AsyncSession) -> Settings:
    result = await db.execute(select(Settings).limit(1))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = Settings()
        db.add(settings)
        await db.flush()
        await db.refresh(settings)
    return settings


@router.get("/song/{song_id}/pdf")
async def export_song_pdf(
    song_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    settings = await get_global_settings(db)
    song_model = ST.from_chordpro(song.body)
    pdf = generate_song_pdf(song_model, settings=settings)
    return Response(
        content=pdf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{song.title}.pdf"'},
    )


@router.get("/songbook/{songbook_id}/pdf")
async def export_songbook_pdf(
    songbook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Songbook)
        .where(Songbook.id == songbook_id)
        .options(selectinload(Songbook.entries).selectinload(SongbookEntry.song))
    )
    songbook = result.scalar_one_or_none()
    if not songbook:
        raise HTTPException(status_code=404, detail="Songbook not found")
    settings = await get_global_settings(db)
    songs = []
    for entry in sorted(songbook.entries, key=lambda e: e.sort_order):
        song_model = ST.from_chordpro(entry.song.body)
        songs.append(song_model)
    pdf = generate_songbook_pdf(songs, settings=settings, title=songbook.name, description=songbook.description or "")
    return Response(
        content=pdf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{songbook.name}.pdf"'},
    )
