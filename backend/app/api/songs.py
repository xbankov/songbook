import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import Response, PlainTextResponse, FileResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.song import Song, SongVersion
from app.models.tag import Tag, song_tags
from app.schemas.song import (
    SongCreate,
    SongOut,
    SongUpdate,
    SongVersionOut,
)
from app.services.scraper import import_from_url
from app.services.converters import (
    chordpro_to_text,
    chordpro_to_abc,
    chordpro_to_ly,
    export_songs_as_chordpro,
    parse_bulk_chordpro,
)

router = APIRouter(prefix="/api/songs", tags=["songs"])


@router.get("", response_model=list[SongOut])
async def list_songs(
    search: str | None = Query(None),
    artist: str | None = Query(None),
    tag: str | None = Query(None),
    sort: str = Query("updated_at"),
    order: str = Query("desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Song)
    if search:
        query = query.where(
            Song.title.ilike(f"%{search}%") | Song.artist.ilike(f"%{search}%")
        )
    if artist:
        query = query.where(Song.artist.ilike(f"%{artist}%"))
    if tag:
        query = query.join(song_tags).join(Tag).where(Tag.name == tag)
    sort_col = getattr(Song, sort, Song.updated_at)
    if order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=SongOut, status_code=status.HTTP_201_CREATED)
async def create_song(body: SongCreate, db: AsyncSession = Depends(get_db)):
    song = Song(
        title=body.title,
        artist=body.artist,
        capo=body.capo,
        key=body.key,
        body=body.body,
        metadata_=body.metadata if hasattr(body, "metadata_") else {},
    )
    db.add(song)
    await db.flush()
    await db.refresh(song)

    version = SongVersion(
        song_id=song.id,
        version=1,
        title=song.title,
        artist=song.artist,
        capo=song.capo,
        key=song.key,
        body=song.body,
    )
    db.add(version)
    await db.flush()
    await db.refresh(song)
    return song


@router.post("/import", response_model=SongOut, status_code=status.HTTP_201_CREATED)
async def import_song(url: str, db: AsyncSession = Depends(get_db)):
    song_model = import_from_url(url)
    if song_model is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to import song from URL")
    body = str(song_model)
    song = Song(
        title=song_model.title,
        artist=song_model.artist,
        capo=song_model.capo,
        key=song_model.key,
        body=body,
        metadata_={"imported_from": url},
    )
    db.add(song)
    await db.flush()
    await db.refresh(song)

    version = SongVersion(
        song_id=song.id,
        version=1,
        title=song.title,
        artist=song.artist,
        capo=song.capo,
        key=song.key,
        body=song.body,
    )
    db.add(version)
    await db.flush()
    await db.refresh(song)
    return song


@router.get("/{song_id}", response_model=SongOut)
async def get_song(song_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    return song


@router.put("/{song_id}", response_model=SongOut)
async def update_song(song_id: uuid.UUID, body: SongUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")

    for field, value in body.model_dump(exclude_none=True, by_alias=True).items():
        setattr(song, field, value)

    song.version += 1

    version = SongVersion(
        song_id=song.id,
        version=song.version,
        title=song.title,
        artist=song.artist,
        capo=song.capo,
        key=song.key,
        body=song.body,
    )
    db.add(version)
    await db.flush()
    await db.refresh(song)
    return song


@router.delete("/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_song(song_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    await db.delete(song)
    await db.flush()


@router.get("/{song_id}/versions", response_model=list[SongVersionOut])
async def list_versions(song_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SongVersion)
        .where(SongVersion.song_id == song_id)
        .order_by(SongVersion.version.desc())
    )
    return result.scalars().all()


@router.get("/{song_id}/versions/{version_number}", response_model=SongVersionOut)
async def get_version(song_id: uuid.UUID, version_number: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SongVersion).where(
            SongVersion.song_id == song_id, SongVersion.version == version_number
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    return version


@router.get("/{song_id}/analyze")
async def analyze_song(song_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    from app.services.music_theory import SongModel as ST, detect_key
    model = ST.from_chordpro(song.body)
    k = detect_key(model)
    return {"suggested_key": k[0] if k else None, "confidence": k[1] if k else None}


@router.post("/{song_id}/audio", status_code=status.HTTP_200_OK)
async def upload_audio(
    song_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    os.makedirs(settings.upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "audio.mp3")[1] or ".mp3"
    filename = f"{song_id}{ext}"
    filepath = os.path.join(settings.upload_dir, filename)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    meta = dict(song.metadata_) if song.metadata_ else {}
    meta["audio_file"] = filename
    song.metadata_ = meta
    await db.flush()
    await db.refresh(song)
    return {"audio_file": filename, "size": len(content)}


@router.get("/{song_id}/audio")
async def get_audio(song_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    meta = song.metadata_ or {}
    audio_file = meta.get("audio_file")
    if not audio_file:
        raise HTTPException(status_code=404, detail="No audio file")
    filepath = os.path.join(settings.upload_dir, audio_file)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(filepath)


@router.delete("/{song_id}/audio", status_code=status.HTTP_200_OK)
async def delete_audio(song_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    meta = dict(song.metadata_) if song.metadata_ else {}
    audio_file = meta.pop("audio_file", None)
    song.metadata_ = meta
    if audio_file:
        filepath = os.path.join(settings.upload_dir, audio_file)
        if os.path.exists(filepath):
            os.remove(filepath)
    await db.flush()
    return {"status": "ok"}


@router.get("/export/bulk")
async def bulk_export(
    format: str = Query("chordpro"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Song).order_by(Song.artist, Song.title))
    songs = result.scalars().all()
    from app.services.music_theory import SongModel as ST
    models = [ST.from_chordpro(s.body) for s in songs]

    if format == "text":
        content = "\n\n".join(chordpro_to_text(m) for m in models)
        media = "text/plain"
    elif format == "abc":
        content = "\n\n".join(chordpro_to_abc(m) for m in models)
        media = "text/plain"
    elif format == "lilypond":
        content = "\n\n".join(chordpro_to_ly(m) for m in models)
        media = "text/plain"
    else:
        content = export_songs_as_chordpro(models)
        media = "text/plain"

    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f"attachment; filename=songs.{format}"},
    )


@router.post("/import/bulk", response_model=list[SongOut], status_code=status.HTTP_201_CREATED)
async def bulk_import(
    body: str,
    db: AsyncSession = Depends(get_db),
):
    models = parse_bulk_chordpro(body)
    created = []
    for m in models:
        song = Song(
            title=m.title,
            artist=m.artist,
            capo=m.capo,
            key=m.key,
            body=str(m),
        )
        db.add(song)
        await db.flush()
        version = SongVersion(
            song_id=song.id,
            version=1,
            title=song.title,
            artist=song.artist,
            capo=song.capo,
            key=song.key,
            body=song.body,
        )
        db.add(version)
        await db.flush()
        await db.refresh(song)
        created.append(song)
    return created


@router.get("/{song_id}/export")
async def export_song_format(
    song_id: uuid.UUID,
    format: str = Query("chordpro"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    from app.services.music_theory import SongModel as ST
    model = ST.from_chordpro(song.body)

    if format == "text":
        content = chordpro_to_text(model)
    elif format == "abc":
        content = chordpro_to_abc(model)
    elif format == "lilypond":
        content = chordpro_to_ly(model)
    else:
        content = str(model)

    return PlainTextResponse(
        content=content,
        headers={"Content-Disposition": f"attachment; filename=\"{song.title}.{format}\""},
    )


@router.get("/{song_id}/transpose", response_model=SongOut)
async def transpose_song(
    song_id: uuid.UUID,
    interval: int = Query(..., description="Semitones to transpose"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    from app.services.music_theory import SongModel as ST
    model = ST.from_chordpro(song.body)
    transposed = model.transpose(interval)
    song.body = str(transposed)
    song.version += 1
    version = SongVersion(
        song_id=song.id,
        version=song.version,
        title=song.title,
        artist=song.artist,
        capo=song.capo,
        key=song.key,
        body=song.body,
    )
    db.add(version)
    await db.flush()
    await db.refresh(song)
    return song
