"""Batch upload of ChordPro and chords-over-lyrics files (#29).

The browser uploads the files twice: first for a dry run that lists what each
file would become, then for the import of the chosen entries. Parsing is
deterministic, so both passes agree without keeping state on the server.

Hostile input is rejected or reported per entry: never written to disk, never
trusted from the archive headers. A file that cannot be read becomes an entry
with an error instead of failing the whole upload.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath
from typing import Iterable, Sequence

from app.services.converters import (
    chordpro_body,
    parse_capo,
    split_chordpro_metadata,
)
from app.services.music_theory import Chord, SongModel
from app.services.ultimate_guitar import parse_content

ALLOWED_EXTENSIONS = (".cho", ".crd", ".chordpro", ".pro", ".txt")

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # all uploaded files in one request
MAX_TEXT_BYTES = 2 * 1024 * 1024  # one song file, also inside a zip
MAX_UNCOMPRESSED_BYTES = 60 * 1024 * 1024  # everything one zip may hold
MAX_FILES = 300  # uploaded files plus zip members

_BRACKET = re.compile(r"\[([^\[\]\n]{1,16})\]")
# One ChordPro directive on its own line, e.g. "{start_of_chorus}".
_DIRECTIVE = re.compile(r"^\s*\{[A-Za-z_][^{}]*\}\s*$")
_JUNK_NAMES = (".DS_Store", "Thumbs.db", "desktop.ini")
_TRACK_NUMBER = re.compile(r"^\s*\d+\s*[-._)]+\s*")
# Words that look like a chord to the lenient parser but label a section.
_SECTION_WORD = re.compile(
    r"(?i)^(?:chorus|verse|bridge|refrain|pre-?chorus|intro|outro|solo|interlude|"
    r"break|breakdown|ending|tag|vamp|coda|instrumental)\b"
)


class BatchImportError(Exception):
    """The upload cannot be read at all; the message is shown to the user."""


@dataclass
class Upload:
    name: str
    data: bytes
    error: str | None = None


@dataclass
class BatchEntry:
    """One song found in the upload, or why it could not be read."""

    index: int
    filename: str
    title: str = "Unknown"
    artist: str = "Unknown"
    capo: int = 0
    key: str | None = None
    body: str = ""
    error: str | None = None
    duplicate: bool = False

    def preview(self) -> dict:
        return {
            "index": self.index,
            "filename": self.filename,
            "title": self.title,
            "artist": self.artist,
            "capo": self.capo,
            "key": self.key,
            "duplicate": self.duplicate,
            "error": self.error,
        }


def identity(title: str, artist: str) -> tuple[str, str]:
    """Case- and space-insensitive key for 'the same title and artist'."""

    def normalise(value: str) -> str:
        return " ".join(value.split()).casefold()

    return normalise(title), normalise(artist)


def mark_duplicates(
    entries: Sequence[BatchEntry], known: Iterable[tuple[str, str]]
) -> None:
    """Flag entries already in the library or earlier in the same upload."""
    seen = {identity(title, artist) for title, artist in known}
    for entry in entries:
        if entry.error:
            continue
        key = identity(entry.title, entry.artist)
        if key in seen:
            entry.duplicate = True
        seen.add(key)


def parse_selection(value: str | None, count: int) -> set[int]:
    """Indices the user chose; a missing selection means every entry."""
    if value is None:
        return set(range(count))
    chosen = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            index = int(part)
        except ValueError as e:
            raise BatchImportError("Invalid selection.") from e
        if 0 <= index < count:
            chosen.add(index)
    return chosen


def collect_entries(uploads: Sequence[Upload]) -> list[BatchEntry]:
    """Expand zips and parse every song file, in upload order."""
    entries = []
    for upload in expand(uploads):
        entries.append(_entry(len(entries), upload))
    return entries


def expand(uploads: Sequence[Upload]) -> list[Upload]:
    """Zip members in place of the archives they came from."""
    files: list[Upload] = []
    received = 0
    for upload in uploads:
        received += len(upload.data)
        if received > MAX_UPLOAD_BYTES:
            raise BatchImportError(
                f"The upload is too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB)."
            )
        if upload.name.lower().endswith(".zip"):
            files.extend(_unpack(upload))
        else:
            files.append(upload)
        if len(files) > MAX_FILES:
            raise BatchImportError(f"Too many files (max {MAX_FILES}).")
    return files


def _unpack(upload: Upload) -> list[Upload]:
    try:
        archive = zipfile.ZipFile(BytesIO(upload.data))
    except zipfile.BadZipFile as e:
        raise BatchImportError(f"{upload.name} is not a readable zip archive.") from e

    members: list[Upload] = []
    total = 0
    with archive:
        infos = [
            info
            for info in archive.infolist()
            if not info.is_dir() and not _is_junk(info.filename)
        ]
        if len(infos) > MAX_FILES:
            raise BatchImportError(
                f"{upload.name} has too many files (max {MAX_FILES})."
            )
        for info in infos:
            if _is_unsafe(info.filename):
                raise BatchImportError(
                    f"{upload.name} contains an unsafe path: {info.filename}"
                )
            name = PurePosixPath(info.filename).name
            if info.flag_bits & 0x1:
                members.append(Upload(name, b"", "Encrypted files are not supported."))
                continue
            if info.file_size > MAX_TEXT_BYTES:
                members.append(Upload(name, b"", _too_large()))
                continue
            with archive.open(info) as member:
                # Do not trust the declared size: read at most one byte over.
                data = member.read(MAX_TEXT_BYTES + 1)
            if len(data) > MAX_TEXT_BYTES:
                members.append(Upload(name, b"", _too_large()))
                continue
            # Count the bytes actually unpacked, not the (possibly lying) header.
            total += len(data)
            if total > MAX_UNCOMPRESSED_BYTES:
                raise BatchImportError(f"{upload.name} is too large once unpacked.")
            members.append(Upload(name, data))
    return members


def _is_junk(name: str) -> bool:
    parts = PurePosixPath(name).parts
    return bool(parts) and (
        parts[0] == "__MACOSX" or PurePosixPath(name).name in _JUNK_NAMES
    )


def _is_unsafe(name: str) -> bool:
    """A path we would not unpack: absolute, a drive letter, or a parent hop."""
    if not name or name.startswith(("/", "\\")) or "\\" in name or "\x00" in name:
        return True
    parts = PurePosixPath(name).parts
    return any(part == ".." for part in parts) or ":" in parts[0]


def _too_large() -> str:
    return f"File is too large (max {MAX_TEXT_BYTES // (1024 * 1024)} MB)."


def _entry(index: int, upload: Upload) -> BatchEntry:
    entry = BatchEntry(
        index=index,
        filename=upload.name,
        title=_title_from_name(upload.name),
    )
    if upload.error:
        entry.error = upload.error
        return entry

    suffix = PurePosixPath(upload.name).suffix.lower()
    if suffix == ".zip":
        entry.error = "Nested zip archives are not unpacked."
        return entry
    if suffix not in ALLOWED_EXTENSIONS:
        entry.error = (
            f"Unsupported file type {suffix or '(none)'}: "
            f"use {', '.join(ALLOWED_EXTENSIONS)} or .zip."
        )
        return entry
    if len(upload.data) > MAX_TEXT_BYTES:
        entry.error = _too_large()
        return entry
    try:
        text = _decode(upload.data)
    except ValueError as e:
        entry.error = str(e)
        return entry

    try:
        song, body = _parse_song(entry.title, text)
    except (KeyError, IndexError, ValueError):
        entry.error = "Could not read the song in this file."
        return entry
    if not has_text(song):
        entry.error = "No song text found in this file."
        return entry

    entry.title = song.title[:512]
    entry.artist = (song.artist or "Unknown")[:512]
    entry.capo = song.capo
    entry.key = song.key
    entry.body = body
    return entry


def _decode(data: bytes) -> str:
    if b"\x00" in data:
        raise ValueError("This is not a text file.")
    for encoding in ("utf-8-sig", "cp1250"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not read the text: it is neither UTF-8 nor Windows-1250.")


def _title_from_name(name: str) -> str:
    stem = _TRACK_NUMBER.sub("", PurePosixPath(name).stem).replace("_", " ").strip()
    return (stem or "Unknown")[:512]


def has_text(song: SongModel) -> bool:
    return any(str(line).strip() for section in song.sections for line in section.lines)


def _parse_song(title: str, text: str) -> tuple[SongModel, str]:
    """The song and its stored body.

    ChordPro keeps its other directives ({comment}, {tempo}, ...): only the
    metadata tags are taken out of the body, as when a song is saved (#37).
    Plain text goes through the shared UG parser, which merges chord lines.
    """
    if _is_chordpro(text):
        body, tags = split_chordpro_metadata(text)
        song = SongModel.from_chordpro(body).model_copy(
            update={
                "title": tags.get("title") or title,
                "artist": tags.get("artist") or "Unknown",
                "capo": parse_capo(tags.get("capo")) or 0,
                "key": tags.get("key"),
            }
        )
        return song, body
    song = SongModel(
        sections=parse_content(_mark_chords(text)), title=title, artist="Unknown"
    )
    return song, chordpro_body(song)


def _is_chordpro(text: str) -> bool:
    if any(_DIRECTIVE.match(line) for line in text.splitlines()):
        return True
    return any(_is_chord_token(match.group(1)) for match in _BRACKET.finditer(text))


def _is_chord_token(token: str) -> bool:
    # Chord.parse is lenient: "Chorus" has a C root and an unknown quality,
    # so words that label a section are excluded by name first.
    if _SECTION_WORD.match(token.strip("[](){}:.,")):
        return False
    try:
        Chord.parse(token.strip())
    except (KeyError, IndexError, ValueError):
        return False
    return True


def _mark_chords(text: str) -> str:
    """Wrap plain chord lines in the ``[ch]`` markup the shared parser reads."""
    lines = []
    for line in text.split("\n"):
        tokens = line.split()
        if tokens and all(_is_chord_token(token) for token in tokens):
            line = re.sub(r"[^\s]+", lambda m: f"[ch]{m.group(0)}[/ch]", line)
        lines.append(line)
    return "\n".join(lines)
