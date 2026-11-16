import os
import uuid

from app.database import get_db
from app.models.song import Song, SongVersion
from app.models.tag import Tag, song_tags
from app.schemas.song import (
    SongCreate,
    SongIdsRequest,
    SongOut,
    SongUpdate,
    SongVersionOut,
)
from app.services.converters import (
    METADATA_TAGS,
    absorb_chordpro_metadata,
    chordpro_body,
    chordpro_to_abc,
    chordpro_to_ly,
    chordpro_to_text,
    ensure_chordpro_metadata,
    export_songs_as_chordpro,
    parse_bulk_chordpro,
    song_model_from_row,
    transpose_chordpro_body,
    transpose_key,
)
from app.services.http import content_disposition
from app.services.scraper import import_from_url
from app.services.settings import get_or_create_settings as get_global_settings
from app.services.tags import resolve_tags
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, PlainTextResponse, Response
from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

router = APIRouter(prefix="/api/songs", tags=["songs"])


@router.get("", response_model=list[SongOut])
async def list_songs(
    response: Response,
    search: str | None = Query(None),
    artist: str | None = Query(None),
    tag: str | None = Query(None),
    difficulty: str | None = Query(None),
    genre: str | None = Query(None),
    letter: str | None = Query(
        None, min_length=1, max_length=1, pattern=r"^[A-Za-z#]$"
    ),
    sort: str = Query("updated_at"),
    order: str = Query("desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    def has_tag(name: str) -> ColumnElement[bool]:
        return exists(
            select(1)
            .select_from(song_tags.join(Tag, Tag.id == song_tags.c.tag_id))
            .where(song_tags.c.song_id == Song.id, Tag.name == name)
        )

    query = select(Song)
    if search:
        query = query.where(
            Song.title.ilike(f"%{search}%") | Song.artist.ilike(f"%{search}%")
        )
    if artist:
        query = query.where(Song.artist.ilike(f"%{artist}%"))
    if tag:
        query = query.where(has_tag(tag.strip()))
    if difficulty:
        query = query.where(has_tag(f"difficulty:{difficulty.strip().lower()}"))
    if genre:
        query = query.where(has_tag(f"genre:{genre.strip().lower()}"))
    if letter == "#":
        query = query.where(Song.title.op("!~")("^[A-Za-z]"))
    elif letter:
        query = query.where(Song.title.ilike(f"{letter}%"))
    total_column = func.count().over().label("total")
    query = query.add_columns(total_column)
    sort_col = getattr(Song, sort, Song.updated_at)
    if order == "asc":
        query = query.order_by(sort_col.asc(), Song.id.asc())
    else:
        query = query.order_by(sort_col.desc(), Song.id.desc())
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()
    items = [row[0] for row in rows]
    total = rows[0][1] if rows else 0
    response.headers["X-Total-Count"] = str(total)
    return items


@router.post("", response_model=SongOut, status_code=status.HTTP_201_CREATED)
async def create_song(body: SongCreate, db: AsyncSession = Depends(get_db)):
    tags = await resolve_tags(db, body.tags)
    # A pasted body may carry {title}/{artist}/{capo}/{key}: move them into
    # the fields the request left unset. The default capo 0 means "not set".
    clean_body, fields = absorb_chordpro_metadata(
        body.body,
        {
            "title": body.title,
            "artist": body.artist,
            "capo": body.capo or None,
            "key": body.key,
        },
    )
    song = Song(
        title=fields["title"],
        artist=fields["artist"],
        capo=fields["capo"] or 0,
        key=fields["key"] or None,
        body=clean_body,
        metadata_=body.metadata if hasattr(body, "metadata_") else {},
        tags=tags,
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to import song from URL",
        )
    body = chordpro_body(song_model)
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Song not found"
        )
    return song


@router.put("/{song_id}", response_model=SongOut)
async def update_song(
    song_id: uuid.UUID, body: SongUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Song).where(Song.id == song_id).with_for_update())
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Song not found"
        )

    data = body.model_dump(exclude_none=True, by_alias=True)
    for field in ("title", "artist"):
        if field in data and not data[field].strip():
            del data[field]
    if "body" in data:
        # A pasted body may carry metadata tags. Fields sent with the request
        # win, then the song's stored fields; a tag only fills an unset field.
        data["body"], resolved = absorb_chordpro_metadata(
            data["body"],
            {tag: data.get(tag, getattr(song, tag)) for tag in METADATA_TAGS},
        )
        data.update({k: v for k, v in resolved.items() if v is not None})
    tag_names = data.pop("tags", None)
    for field, value in data.items():
        setattr(song, field, value)
    if tag_names is not None:
        song.tags = await resolve_tags(db, tag_names)

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Song not found"
        )
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
async def get_version(
    song_id: uuid.UUID, version_number: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SongVersion).where(
            SongVersion.song_id == song_id, SongVersion.version == version_number
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Version not found"
        )
    return version


@router.post("/{song_id}/versions/{version_number}/restore", response_model=SongOut)
async def restore_version(
    song_id: uuid.UUID, version_number: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Song).where(Song.id == song_id).with_for_update())
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Song not found"
        )

    result = await db.execute(
        select(SongVersion).where(
            SongVersion.song_id == song_id, SongVersion.version == version_number
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Version not found"
        )

    song.title = version.title
    song.artist = version.artist
    song.capo = version.capo
    song.key = version.key
    song.body = version.body
    song.version += 1

    restored = SongVersion(
        song_id=song.id,
        version=song.version,
        title=song.title,
        artist=song.artist,
        capo=song.capo,
        key=song.key,
        body=song.body,
    )
    db.add(restored)
    await db.flush()
    await db.refresh(song)
    return song


@router.post("/{song_id}/versions/{version_number}/favorite", response_model=SongOut)
async def favorite_version(
    song_id: uuid.UUID, version_number: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Song).where(Song.id == song_id).with_for_update())
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Song not found"
        )
    result = await db.execute(
        select(SongVersion).where(
            SongVersion.song_id == song_id, SongVersion.version == version_number
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Version not found"
        )
    meta = dict(song.metadata_ or {})
    favorites = set(meta.get("favorite_versions", []))
    favorites.add(version_number)
    meta["favorite_versions"] = sorted(favorites)
    song.metadata_ = meta
    await db.flush()
    await db.refresh(song)
    return song


@router.delete("/{song_id}/versions/{version_number}/favorite", response_model=SongOut)
async def unfavorite_version(
    song_id: uuid.UUID, version_number: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Song).where(Song.id == song_id).with_for_update())
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Song not found"
        )
    meta = dict(song.metadata_ or {})
    favorites = set(meta.get("favorite_versions", []))
    favorites.discard(version_number)
    meta["favorite_versions"] = sorted(favorites)
    song.metadata_ = meta
    await db.flush()
    await db.refresh(song)
    return song


@router.post(
    "/{song_id}/versions/{version_number}/fork",
    response_model=SongOut,
    status_code=status.HTTP_201_CREATED,
)
async def fork_version(
    song_id: uuid.UUID, version_number: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Song not found"
        )
    result = await db.execute(
        select(SongVersion).where(
            SongVersion.song_id == song_id, SongVersion.version == version_number
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Version not found"
        )

    forked = Song(
        title=f"{version.title} (fork)",
        artist=version.artist,
        capo=version.capo,
        key=version.key,
        body=version.body,
        metadata_={
            "forked_from": str(song.id),
            "forked_version": version_number,
        },
        version=1,
    )
    db.add(forked)
    await db.flush()
    db.add(
        SongVersion(
            song_id=forked.id,
            version=1,
            title=forked.title,
            artist=forked.artist,
            capo=forked.capo,
            key=forked.key,
            body=forked.body,
        )
    )
    await db.flush()
    await db.refresh(forked)
    return forked


@router.get("/{song_id}/analyze")
async def analyze_song(song_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Song not found"
        )
    from app.services.music_theory import SongModel as ST
    from app.services.music_theory import detect_key

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Song not found"
        )
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Song not found"
        )
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Song not found"
        )
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
    models = [song_model_from_row(s) for s in songs]

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
        # Keep the stored body (with {comment}, {tempo}, ...) like the other
        # ChordPro exports; only the metadata header comes from the fields.
        content = "\n\n---\n\n".join(
            ensure_chordpro_metadata(s.body, s.title, s.artist, s.capo, s.key)
            for s in songs
        )
        media = "text/plain"

    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": content_disposition(f"songs.{format}")},
    )


@router.post(
    "/import/bulk", response_model=list[SongOut], status_code=status.HTTP_201_CREATED
)
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
            body=chordpro_body(m),
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


@router.post("/export/selected")
async def export_selected_songs(
    body: SongIdsRequest,
    format: str = Query("chordpro"),
    db: AsyncSession = Depends(get_db),
):
    ids = list(dict.fromkeys(body.ids))
    result = await db.execute(select(Song).where(Song.id.in_(ids)))
    by_id = {str(song.id): song for song in result.scalars().all()}
    missing = [str(song_id) for song_id in ids if str(song_id) not in by_id]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Songs not found: {', '.join(missing)}",
        )
    selected = [by_id[str(song_id)] for song_id in ids]
    settings = await get_global_settings(db)

    if format == "chordpro":
        parts = []
        for song in selected:
            body = ensure_chordpro_metadata(
                song.body, song.title, song.artist, song.capo, song.key
            )
            parts.append(transpose_chordpro_body(body, settings.transpose))
        content = "\n\n---\n\n".join(parts)
        extension = "cho"
    else:
        models = []
        for song in selected:
            model = song_model_from_row(song)
            if settings.transpose:
                model = model.transpose(settings.transpose)
            models.append(model)
        if format == "text":
            content = "\n\n".join(chordpro_to_text(model) for model in models)
        elif format == "abc":
            content = "\n\n".join(chordpro_to_abc(model) for model in models)
        elif format == "lilypond":
            content = "\n\n".join(chordpro_to_ly(model) for model in models)
        else:
            content = export_songs_as_chordpro(models)
        extension = format

    return Response(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": content_disposition(f"selected.{extension}")},
    )


@router.get("/{song_id}/export")
async def export_song_format(
    song_id: uuid.UUID,
    format: str = Query("chordpro"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Song not found"
        )
    settings = await get_global_settings(db)
    model = song_model_from_row(song)
    if settings.transpose:
        model = model.transpose(settings.transpose)

    if format == "text":
        content = chordpro_to_text(model)
    elif format == "abc":
        content = chordpro_to_abc(model)
    elif format == "lilypond":
        content = chordpro_to_ly(model)
    else:
        content = transpose_chordpro_body(
            ensure_chordpro_metadata(
                song.body, song.title, song.artist, song.capo, song.key
            ),
            settings.transpose,
        )

    return PlainTextResponse(
        content=content,
        headers={"Content-Disposition": content_disposition(f"{song.title}.{format}")},
    )


@router.get("/{song_id}/transpose", response_model=SongOut)
async def transpose_song(
    song_id: uuid.UUID,
    interval: int = Query(..., description="Semitones to transpose"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Song).where(Song.id == song_id).with_for_update())
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Song not found"
        )
    # Transpose the stored text instead of round-tripping it through SongModel,
    # which drops directives such as {comment} and {tempo}.
    song.body = transpose_chordpro_body(song.body, interval)
    song.key = transpose_key(song.key, interval)
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
