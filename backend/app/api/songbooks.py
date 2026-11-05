import uuid

from app.database import get_db
from app.models.song import Song
from app.models.songbook import Songbook, SongbookEntry
from app.schemas.songbook import (
    SongbookCreate,
    SongbookDetailOut,
    SongbookEntryOut,
    SongbookEntryUpdate,
    SongbookOut,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/api/songbooks", tags=["songbooks"])


@router.get("", response_model=list[SongbookOut])
async def list_songbooks(
    sort: str = Query("updated_at"),
    order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
):
    query = select(Songbook)
    sort_col = getattr(Songbook, sort, Songbook.updated_at)
    if order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=SongbookOut, status_code=status.HTTP_201_CREATED)
async def create_songbook(body: SongbookCreate, db: AsyncSession = Depends(get_db)):
    songbook = Songbook(name=body.name, description=body.description)
    db.add(songbook)
    await db.flush()
    await db.refresh(songbook)
    return songbook


@router.get("/{songbook_id}", response_model=SongbookDetailOut)
async def get_songbook(songbook_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Songbook)
        .where(Songbook.id == songbook_id)
        .options(selectinload(Songbook.entries).selectinload(SongbookEntry.song))
    )
    songbook = result.scalar_one_or_none()
    if not songbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Songbook not found"
        )
    return songbook


@router.put("/{songbook_id}", response_model=SongbookOut)
async def update_songbook(
    songbook_id: uuid.UUID, body: SongbookCreate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Songbook).where(Songbook.id == songbook_id))
    songbook = result.scalar_one_or_none()
    if not songbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Songbook not found"
        )
    songbook.name = body.name
    songbook.description = body.description
    await db.flush()
    await db.refresh(songbook)
    return songbook


@router.delete("/{songbook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_songbook(songbook_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Songbook).where(Songbook.id == songbook_id))
    songbook = result.scalar_one_or_none()
    if not songbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Songbook not found"
        )
    await db.delete(songbook)
    await db.flush()


@router.post(
    "/{songbook_id}/songs",
    response_model=SongbookEntryOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_song_to_songbook(
    songbook_id: uuid.UUID,
    song_id: uuid.UUID,
    sort_order: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    songbook_result = await db.execute(
        select(Songbook).where(Songbook.id == songbook_id)
    )
    songbook = songbook_result.scalar_one_or_none()
    if not songbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Songbook not found"
        )
    song_result = await db.execute(select(Song).where(Song.id == song_id))
    song = song_result.scalar_one_or_none()
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Song not found"
        )
    if sort_order is None:
        result = await db.execute(
            select(SongbookEntry)
            .where(SongbookEntry.songbook_id == songbook_id)
            .order_by(SongbookEntry.sort_order.desc())
            .limit(1)
        )
        last_entry = result.scalar_one_or_none()
        sort_order = (last_entry.sort_order + 1) if last_entry else 0
    entry = SongbookEntry(
        songbook_id=songbook_id, song_id=song_id, sort_order=sort_order
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


@router.delete(
    "/{songbook_id}/songs/{entry_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_song_from_songbook(
    songbook_id: uuid.UUID, entry_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SongbookEntry).where(
            SongbookEntry.id == entry_id, SongbookEntry.songbook_id == songbook_id
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found"
        )
    await db.delete(entry)
    await db.flush()


@router.put("/{songbook_id}/songs/{entry_id}", response_model=SongbookEntryOut)
async def update_songbook_entry(
    songbook_id: uuid.UUID,
    entry_id: uuid.UUID,
    body: SongbookEntryUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SongbookEntry).where(
            SongbookEntry.id == entry_id, SongbookEntry.songbook_id == songbook_id
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found"
        )
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(entry, field, value)
    await db.flush()
    await db.refresh(entry)
    return entry
