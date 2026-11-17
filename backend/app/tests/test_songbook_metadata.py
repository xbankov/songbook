"""Songbook metadata (#89); the chord chart was removed in #143."""

from datetime import date, datetime, timezone
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

from app.api import export as export_api
from app.api.export import songbook_metadata
from app.database import get_db
from app.main import app
from app.models.songbook import Songbook
from app.schemas.songbook import SongbookUpdate
from app.services.auth import create_access_token
from app.services.music_theory import SongModel
from app.services.pdf import generate_songbook_pdf
from fastapi.testclient import TestClient


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


def test_songbook_pdf_shows_metadata_and_no_chord_chart(monkeypatch):
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
    )

    html = rendered["html"]
    assert "Author:</span> Jane" in html
    assert "Genre:</span> bluegrass" in html
    # The per-songbook chord chart was removed in #143.
    assert 'class="chord-chart"' not in html
    assert ">Chords<" not in html


def test_songbook_metadata_skips_blank_fields():
    songbook = _songbook(author="Jane", date=date(2026, 5, 1), genre=None)

    assert songbook_metadata(songbook) == [("Author", "Jane"), ("Date", "2026-05-01")]


def test_schema_turns_blank_metadata_into_null():
    update = SongbookUpdate(author="  ", genre=" folk ")

    assert update.author is None
    assert update.genre == "folk"


def test_update_songbook_saves_metadata():
    songbook = _songbook()

    response = _put(
        songbook,
        {
            "author": "Jane",
            "date": "2026-05-01",
            "genre": "bluegrass",
            "difficulty": "easy",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["author"] == "Jane"
    assert body["date"] == "2026-05-01"
    assert body["genre"] == "bluegrass"
    assert body["difficulty"] == "easy"
    assert body["name"] == "Book"


def test_update_songbook_ignores_null_for_required_fields():
    songbook = _songbook()

    response = _put(songbook, {"name": None, "author": None})

    assert response.status_code == 200
    assert response.json()["name"] == "Book"
    assert response.json()["author"] is None


def test_update_songbook_ignores_the_removed_chord_diagram_setting():
    # The column stays for existing data (#143); the API no longer reads or
    # returns it, so a stale client cannot change it.
    songbook = _songbook(chord_diagrams="all")

    response = _put(songbook, {"chord_diagrams": "none"})

    assert response.status_code == 200
    assert "chord_diagrams" not in response.json()
    assert songbook.chord_diagrams == "all"


def test_songbook_has_no_chord_chart_endpoint():
    response = TestClient(app).get(
        f"/api/songbooks/{uuid4()}/chords",
        headers={"Authorization": f"Bearer {create_access_token()}"},
    )

    assert response.status_code == 404


def test_songbook_pdf_export_passes_metadata(monkeypatch):
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
    # The stored column no longer affects the PDF.
    assert "chord_diagrams" not in captured
