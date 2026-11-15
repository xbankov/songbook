import uuid

from app.database import get_db
from app.models.song import Song
from app.models.songbook import Songbook, SongbookEntry
from app.services.converters import (
    ensure_chordpro_metadata,
    transpose_chordpro_body,
)
from app.services.http import content_disposition
from app.services.music_theory import SongModel as ST
from app.services.pdf import generate_song_pdf, generate_songbook_pdf
from app.services.settings import get_or_create_settings as get_global_settings
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/api/export", tags=["export"])


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
        headers={
            "Content-Disposition": content_disposition(f"{song.title}.pdf", inline=True)
        },
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
    per_song = []
    for entry in sorted(songbook.entries, key=lambda e: e.sort_order):
        song_model = ST.from_chordpro(entry.song.body)
        songs.append(song_model)
        per_song.append(
            {
                "transpose": entry.transpose,
                "double_column": bool(entry.double_column)
                or bool(settings.double_column),
            }
        )
    pdf = generate_songbook_pdf(
        songs,
        settings=settings,
        title=songbook.name,
        description=songbook.description or "",
        per_song=per_song,
    )
    return Response(
        content=pdf.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": content_disposition(
                f"{songbook.name}.pdf", inline=True
            )
        },
    )


@router.get("/songbook/{songbook_id}/chordpro")
async def export_songbook_chordpro(
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
    for entry in sorted(
        songbook.entries, key=lambda item: (item.sort_order, str(item.id))
    ):
        if entry.song is None:
            continue
        body = ensure_chordpro_metadata(
            entry.song.body, entry.song.title, entry.song.artist
        )
        songs.append(
            transpose_chordpro_body(body, settings.transpose + entry.transpose)
        )
    content = "\n\n---\n\n".join(songs)
    return Response(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": content_disposition(f"{songbook.name}.cho")},
    )
