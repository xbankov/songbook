"""Batch upload of ChordPro and chords-over-lyrics files (#29)."""

import io
import zipfile
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from app.database import get_db
from app.main import app
from app.models.song import Song, SongVersion
from app.services import batch_import
from app.services.auth import create_access_token
from app.services.batch_import import (
    BatchImportError,
    Upload,
    collect_entries,
    mark_duplicates,
    parse_selection,
)
from fastapi.testclient import TestClient

CHORDPRO = "\n".join(
    [
        "{title: Wagon Wheel}",
        "{artist: Old Crow Medicine Show}",
        "{capo: 2}",
        "{key: A}",
        "{comment: Banjo kicks off}",
        "{tempo: 120}",
        "{start_of_chorus}",
        "[A]Rock me momma like a [E]wagon wheel",
        "{end_of_chorus}",
    ]
)

PLAIN = "\n".join(
    [
        "Wagon Wheel",
        "",
        "[Verse]",
        "G          D",
        "Heading down south to the land of the pines",
        "Em                    C",
        "Riding my horse into North Caroline",
    ]
)


def _entry(name: str, text: str):
    [entry] = collect_entries([Upload(name, text.encode())])
    return entry


def _zip(members: dict[str, str]) -> Upload:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, text in members.items():
            archive.writestr(name, text)
    return Upload("songs.zip", buffer.getvalue())


def test_chordpro_keeps_its_fields_and_sections():
    entry = _entry("wagon.cho", CHORDPRO)

    assert entry.error is None
    assert (entry.title, entry.artist) == (
        "Wagon Wheel",
        "Old Crow Medicine Show",
    )
    assert (entry.capo, entry.key) == (2, "A")
    assert "{start_of_chorus}" in entry.body
    assert "[A]Rock me momma" in entry.body
    # Only the metadata tags move to the fields; other directives stay.
    assert "{title:" not in entry.body
    assert "{comment: Banjo kicks off}" in entry.body
    assert "{tempo: 120}" in entry.body


def test_plain_chords_merge_into_the_lyrics_at_their_columns():
    entry = _entry("wagon.txt", PLAIN)

    assert entry.error is None
    assert "[G]Heading dow[D]n south to the land of the pines" in entry.body
    assert "[Em]Riding my horse into N[C]orth Caroline" in entry.body
    assert "[ch]" not in entry.body


def test_plain_section_headers_become_chordpro_sections():
    entry = _entry("chorus.txt", "[Chorus]\nG     D\nLa la la")

    assert "{start_of_chorus}" in entry.body
    assert "[G]La la [D]la" in entry.body


def test_a_bare_section_word_is_not_a_chord():
    entry = _entry("song.txt", "Chorus\nG     D\nLa la la")

    assert "{start_of" not in entry.body
    assert "Chorus" in entry.body


def test_unknown_chord_qualities_still_merge():
    entry = _entry("song.txt", "Cadd9    G\nLa la la la la")

    assert "[Cadd9]La la la [G]la la" in entry.body


def test_plain_lyrics_without_chords_still_import():
    entry = _entry("lyrics.txt", "Just a line\nand another one")

    assert entry.error is None
    assert "Just a line" in entry.body


def test_title_falls_back_to_the_file_name():
    entry = _entry("03 - Wagon Wheel.txt", "G\nLa la")

    assert entry.title == "Wagon Wheel"
    assert entry.artist == "Unknown"


def test_cp1250_text_is_decoded():
    entry = _entry("pisen.txt", "Píseň o cestě")

    assert entry.error is None
    assert "Píseň" in entry.body


def test_a_chordpro_file_without_a_title_uses_the_file_name():
    entry = _entry("Old Song.cho", "{capo: 3}\n[G]La")

    assert entry.title == "Old Song"
    assert entry.capo == 3


def test_utf8_bom_is_stripped():
    [entry] = collect_entries([Upload("bom.txt", b"\xef\xbb\xbfLa la")])

    assert entry.error is None
    assert entry.body == "La la"


def test_binary_file_is_an_error_entry():
    entry = _entry("song.txt", "La\x00la")

    assert entry.error == "This is not a text file."


def test_empty_file_is_an_error_entry():
    entry = _entry("empty.txt", "   \n\n")

    assert entry.error == "No song text found in this file."


def test_unsupported_extension_is_an_error_entry():
    entry = _entry("song.doc", "La la")

    assert "Unsupported file type .doc" in entry.error


def test_chordpro_that_cannot_be_read_is_an_error_entry():
    # "[R:]" is a supermusic refrain marker, not a chord.
    entry = _entry("bad.cho", "{title: X}\n[R:] Ahoj")

    assert entry.error == "Could not read the song in this file."


def test_zip_members_are_unpacked_in_order():
    entries = collect_entries([_zip({"pack/one.cho": CHORDPRO, "pack/two.txt": PLAIN})])

    assert [entry.filename for entry in entries] == ["one.cho", "two.txt"]
    assert [entry.error for entry in entries] == [None, None]


def test_zip_skips_macos_junk():
    entries = collect_entries(
        [
            _zip(
                {
                    "__MACOSX/._one.cho": "junk",
                    ".DS_Store": "junk",
                    "one.cho": CHORDPRO,
                }
            )
        ]
    )

    assert [entry.filename for entry in entries] == ["one.cho"]


def test_zip_rejects_a_parent_path():
    with pytest.raises(BatchImportError, match="unsafe path"):
        collect_entries([_zip({"../evil.cho": CHORDPRO})])


def test_zip_rejects_an_absolute_path():
    with pytest.raises(BatchImportError, match="unsafe path"):
        collect_entries([_zip({"/etc/passwd.cho": CHORDPRO})])


def test_zip_rejects_a_windows_drive_path():
    with pytest.raises(BatchImportError, match="unsafe path"):
        collect_entries([_zip({"C:/evil.cho": CHORDPRO})])


def test_a_bad_zip_is_a_clear_error():
    with pytest.raises(BatchImportError, match="not a readable zip"):
        collect_entries([Upload("broken.zip", b"not a zip")])


def test_a_nested_zip_is_an_error_entry():
    entries = collect_entries([_zip({"inner.zip": "PK"})])

    assert entries[0].error == "Nested zip archives are not unpacked."


def test_too_many_files_are_rejected(monkeypatch):
    monkeypatch.setattr(batch_import, "MAX_FILES", 1)

    with pytest.raises(BatchImportError, match="Too many files"):
        collect_entries([Upload("one.cho", CHORDPRO.encode()), Upload("two.cho", b"")])


def test_a_zip_bomb_is_stopped_by_the_uncompressed_limit(monkeypatch):
    monkeypatch.setattr(batch_import, "MAX_UNCOMPRESSED_BYTES", 10)

    with pytest.raises(BatchImportError, match="too large once unpacked"):
        collect_entries([_zip({"one.cho": "12345678", "two.cho": "12345678"})])


def test_an_oversized_zip_member_is_an_error_entry(monkeypatch):
    monkeypatch.setattr(batch_import, "MAX_TEXT_BYTES", 10)

    entries = collect_entries([_zip({"one.cho": "12345678901"})])

    assert "too large" in entries[0].error


def test_an_oversized_upload_is_rejected(monkeypatch):
    monkeypatch.setattr(batch_import, "MAX_UPLOAD_BYTES", 10)

    with pytest.raises(BatchImportError, match="upload is too large"):
        collect_entries([Upload("one.cho", b"123456"), Upload("two.cho", b"123456")])


def test_duplicates_in_the_library_and_in_the_upload_are_flagged():
    entries = [
        _entry("wagon.cho", CHORDPRO),
        _entry("wagon2.cho", CHORDPRO),
        _entry("other.cho", CHORDPRO.replace("Wagon Wheel", "Other Song")),
    ]

    mark_duplicates(entries, [("  wagon   wheel ", "OLD CROW MEDICINE SHOW")])

    assert [entry.duplicate for entry in entries] == [True, True, False]


def test_a_broken_entry_is_not_a_duplicate():
    entries = [_entry("broken.cho", "{title: X}\n[R:] Ahoj")]

    mark_duplicates(entries, [("x", "unknown")])

    assert entries[0].duplicate is False


def test_selection_defaults_to_every_entry():
    assert parse_selection(None, 3) == {0, 1, 2}


def test_selection_ignores_blank_and_out_of_range_values():
    assert parse_selection("0, 2, 9,", 3) == {0, 2}


def test_a_malformed_selection_is_rejected():
    with pytest.raises(BatchImportError, match="Invalid selection"):
        parse_selection("one", 3)


class _Result:
    def __init__(self, value):
        self.value = value

    def all(self):
        return self.value


class _Session:
    def __init__(self, existing: list[tuple[str, str]] | None = None):
        self.existing = existing or []
        self.added: list = []

    async def execute(self, *args, **kwargs):
        return _Result(self.existing)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        now = datetime.now(timezone.utc)
        for obj in self.added:
            if obj.id is None:
                obj.id = uuid4()
            if isinstance(obj, Song):
                obj.version = obj.version or 1
                obj.created_at = obj.created_at or now
                obj.updated_at = obj.updated_at or now
                obj.tags = []

    async def refresh(self, obj):
        pass


def _post(db: _Session, files: list[tuple[str, bytes]], query: str = ""):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        return TestClient(app).post(
            f"/api/songs/import/files{query}",
            files=[("files", (name, data, "text/plain")) for name, data in files],
            headers={"Authorization": f"Bearer {create_access_token()}"},
        )
    finally:
        app.dependency_overrides.clear()


def test_dry_run_lists_the_songs_and_writes_nothing():
    db = _Session([("Test Song", "Old Crow Medicine Show")])

    response = _post(
        db,
        [
            ("wagon.cho", CHORDPRO.encode()),
            ("test song.cho", CHORDPRO.replace("Wagon Wheel", "Test Song").encode()),
        ],
    )

    assert response.status_code == 200
    entries = response.json()["entries"]
    assert [entry["title"] for entry in entries] == ["Wagon Wheel", "Test Song"]
    assert [entry["duplicate"] for entry in entries] == [False, True]
    assert db.added == []


def test_import_creates_only_the_selected_songs():
    db = _Session()

    response = _post(
        db,
        [("wagon.cho", CHORDPRO.encode()), ("two.cho", CHORDPRO.encode())],
        "?dry_run=false&selected=1",
    )

    assert response.status_code == 201
    data = response.json()
    assert [song["title"] for song in data["imported"]] == ["Wagon Wheel"]
    assert data["skipped"] == []
    songs = [obj for obj in db.added if isinstance(obj, Song)]
    versions = [obj for obj in db.added if isinstance(obj, SongVersion)]
    assert len(songs) == 1
    assert len(versions) == 1
    assert versions[0].body == songs[0].body
    assert songs[0].metadata_ == {"imported_from": "two.cho"}


def test_import_reports_an_unreadable_file_instead_of_saving_it():
    db = _Session()

    response = _post(
        db,
        [("bad.doc", b"La la"), ("good.cho", CHORDPRO.encode())],
        "?dry_run=false",
    )

    assert response.status_code == 201
    data = response.json()
    assert [song["title"] for song in data["imported"]] == ["Wagon Wheel"]
    assert data["skipped"][0]["index"] == 0
    assert "Unsupported file type" in data["skipped"][0]["reason"]
    assert len(db.added) == 2


def test_an_upload_over_the_limit_is_a_400(monkeypatch):
    monkeypatch.setattr(batch_import, "MAX_UPLOAD_BYTES", 10)

    response = _post(_Session(), [("one.cho", b"123456"), ("two.cho", b"123456")])

    assert response.status_code == 400
    assert "too large" in response.json()["detail"]
