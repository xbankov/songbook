"""Songbook metadata and chord-diagram selection (#89)."""

from datetime import date, datetime, timezone
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.api import export as export_api
from app.api.export import songbook_metadata
from app.database import get_db
from app.main import app
from app.models.songbook import Songbook
from app.schemas.songbook import SongbookCreate, SongbookUpdate
from app.services.auth import create_access_token
from app.services.chord_diagrams import chord_chart, chord_shape, is_basic_chord
from app.services.music_theory import Chord, SongModel
from app.services.pdf import generate_songbook_pdf
from fastapi.testclient import TestClient
from pydantic import ValidationError


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _Session:
    def __init__(self, songbook: Songbook):
        self.songbook = songbook

    async def execute(self, *args, **kwargs):
        return _Result(self.songbook)

    async def flush(self):
        pass

    async def refresh(self, obj):
        pass


def _songbook(**fields) -> Songbook:
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=uuid4(),
        name="Book",
        description="",
        chord_diagrams="none",
        created_at=now,
        updated_at=now,
    )
    defaults.update(fields)
    songbook = Songbook(**defaults)
    songbook.entries = []
    return songbook


def _put(songbook: Songbook, payload: dict):
    async def override_get_db():
        yield _Session(songbook)

    app.dependency_overrides[get_db] = override_get_db
    try:
        return TestClient(app).put(
            f"/api/songbooks/{songbook.id}",
            json=payload,
            headers={"Authorization": f"Bearer {create_access_token()}"},
        )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("name", "frets"),
    [
        ("G", [3, 2, 0, 0, 0, 3]),
        ("C", [0, 3, 2, 0, 1, 0]),
        ("Am", [0, 0, 2, 2, 1, 0]),
        ("E7", [0, 2, 0, 1, 0, 0]),
    ],
)
def test_chord_shape_uses_open_positions(name, frets):
    assert chord_shape(Chord.parse(name)) == frets


def test_chord_shape_unknown_quality_has_no_diagram():
    assert chord_shape(Chord.parse("Cxyz")) is None


def test_basic_chords_are_plain_major_and_minor_without_bass():
    assert is_basic_chord(Chord.parse("G"))
    assert is_basic_chord(Chord.parse("Am"))
    assert not is_basic_chord(Chord.parse("E7"))
    assert not is_basic_chord(Chord.parse("C/G"))


def test_chord_chart_modes():
    songs = [
        SongModel.from_chordpro("[G]one [Am]two [E7]three"),
        SongModel.from_chordpro("[G]again [Dsus4]four [Cxyz]odd"),
    ]

    assert chord_chart(songs, "none") == []
    assert [c["name"] for c in chord_chart(songs, "all")] == [
        "Am",
        "Dsus4",
        "E7",
        "G",
    ]
    assert [c["name"] for c in chord_chart(songs, "uncommon")] == ["Dsus4", "E7"]


def test_songbook_pdf_shows_metadata_and_transposed_chord_chart(monkeypatch):
    rendered: dict = {}

    class _HTML:
        def __init__(self, string: str):
            rendered["html"] = string

        def write_pdf(self) -> bytes:
            return b"%PDF-1.4"

    import weasyprint

    monkeypatch.setattr(weasyprint, "HTML", _HTML)
    settings = SimpleNamespace(
        transpose=0, double_column=0, font="DejaVu Sans Mono", font_size=9
    )

    generate_songbook_pdf(
        [SongModel.from_chordpro("[G]Hello [E7]world")],
        settings,
        title="Book",
        per_song=[{"transpose": 2}],
        metadata=[("Author", "Jane"), ("Genre", "bluegrass")],
        chord_diagrams="uncommon",
    )

    html = rendered["html"]
    assert "Author:</span> Jane" in html
    assert "Genre:</span> bluegrass" in html
    # Chords are charted after the per-entry transpose (E7 + 2 = F#7).
    assert '<div class="diagram-name">F#7</div>' in html
    assert '<div class="diagram-name">A</div>' not in html


def test_songbook_pdf_without_chart_has_no_chord_page(monkeypatch):
    rendered: dict = {}

    class _HTML:
        def __init__(self, string: str):
            rendered["html"] = string

        def write_pdf(self) -> bytes:
            return b"%PDF-1.4"

    import weasyprint

    monkeypatch.setattr(weasyprint, "HTML", _HTML)
    settings = SimpleNamespace(
        transpose=0, double_column=0, font="DejaVu Sans Mono", font_size=9
    )
    generate_songbook_pdf([SongModel.from_chordpro("[E7]x")], settings)

    assert 'class="chord-chart"' not in rendered["html"]
    assert 'class="songbook-meta"' not in rendered["html"]


def test_songbook_metadata_skips_blank_fields():
    songbook = _songbook(author="Jane", date=date(2026, 5, 1), genre=None)

    assert songbook_metadata(songbook) == [("Author", "Jane"), ("Date", "2026-05-01")]


def test_schema_rejects_unknown_chord_diagram_mode():
    with pytest.raises(ValidationError):
        SongbookCreate(name="Book", chord_diagrams="some")


def test_schema_turns_blank_metadata_into_null():
    update = SongbookUpdate(author="  ", genre=" folk ")

    assert update.author is None
    assert update.genre == "folk"


def test_update_songbook_saves_metadata_and_chord_diagrams():
    songbook = _songbook()

    response = _put(
        songbook,
        {
            "author": "Jane",
            "date": "2026-05-01",
            "genre": "bluegrass",
            "difficulty": "easy",
            "chord_diagrams": "uncommon",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["author"] == "Jane"
    assert body["date"] == "2026-05-01"
    assert body["genre"] == "bluegrass"
    assert body["difficulty"] == "easy"
    assert body["chord_diagrams"] == "uncommon"
    assert body["name"] == "Book"


def test_update_songbook_ignores_null_for_required_fields():
    songbook = _songbook(chord_diagrams="all")

    response = _put(songbook, {"name": None, "chord_diagrams": None, "author": None})

    assert response.status_code == 200
    assert response.json()["name"] == "Book"
    assert response.json()["chord_diagrams"] == "all"


def test_songbook_pdf_export_passes_metadata_and_mode(monkeypatch):
    songbook = _songbook(author="Jane", chord_diagrams="all")
    captured: dict = {}

    async def fake_settings(_db):
        return SimpleNamespace(double_column=0, transpose=0)

    def fake_pdf(songs, **kwargs):
        captured.update(kwargs)
        return BytesIO(b"%PDF-1.4")

    monkeypatch.setattr(export_api, "get_global_settings", fake_settings)
    monkeypatch.setattr(export_api, "generate_songbook_pdf", fake_pdf)

    async def override_get_db():
        yield _Session(songbook)

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = TestClient(app).get(
            f"/api/export/songbook/{songbook.id}/pdf",
            headers={"Authorization": f"Bearer {create_access_token()}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["metadata"] == [("Author", "Jane")]
    assert captured["chord_diagrams"] == "all"
