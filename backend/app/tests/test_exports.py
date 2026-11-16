from datetime import datetime, timezone
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

from app.api import export as export_api
from app.database import get_db
from app.main import app
from app.models.song import Song
from app.models.songbook import Songbook, SongbookEntry
from app.services.auth import create_access_token
from fastapi.testclient import TestClient


class _ListResult:
    def __init__(self, items):
        self.items = items

    def scalars(self):
        return self

    def all(self):
        return self.items


class _OneResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _Session:
    def __init__(self, results):
        self.results = results

    async def execute(self, *args, **kwargs):
        return self.results.pop(0)

    async def flush(self):
        pass

    async def refresh(self, obj):
        pass


def _song(title: str, body: str) -> Song:
    now = datetime.now(timezone.utc)
    song = Song(
        id=uuid4(),
        title=title,
        artist="Artist",
        capo=0,
        key="G",
        body=body,
        metadata_={},
        version=1,
        created_at=now,
        updated_at=now,
    )
    song.tags = []
    return song


def test_selected_chordpro_export_keeps_selection_order():
    first = _song("First Song", "{title: First Song}\n[G]Hello")
    second = _song("Second Song", "{title: Second Song}\n[C]World")
    db = _Session(
        [
            _ListResult([second, first]),
            _OneResult(SimpleNamespace(transpose=0)),
        ]
    )

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = TestClient(app).post(
            "/api/songs/export/selected",
            json={"ids": [str(first.id), str(second.id)]},
            headers={"Authorization": f"Bearer {create_access_token()}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.text.index("First Song") < response.text.index("Second Song")
    assert "selected.cho" in response.headers["content-disposition"]


def test_songbook_pdf_uses_each_entry_column_setting(monkeypatch):
    now = datetime.now(timezone.utc)
    songbook = Songbook(
        id=uuid4(),
        name="Book",
        description="",
        created_at=now,
        updated_at=now,
    )
    single = SongbookEntry(
        id=uuid4(),
        songbook_id=songbook.id,
        song_id=uuid4(),
        sort_order=0,
        transpose=0,
        double_column=0,
    )
    single.song = _song("Single", "{title: Single}\n[G]Hello")
    double = SongbookEntry(
        id=uuid4(),
        songbook_id=songbook.id,
        song_id=uuid4(),
        sort_order=1,
        transpose=0,
        double_column=1,
    )
    double.song = _song("Double", "{title: Double}\n[C]World")
    songbook.entries = [single, double]
    db = _Session([_OneResult(songbook)])
    captured: dict = {}

    async def fake_settings(_db):
        return SimpleNamespace(double_column=1, transpose=0)

    def fake_pdf(songs, **kwargs):
        captured.update(kwargs)
        return BytesIO(b"%PDF-1.4")

    monkeypatch.setattr(export_api, "get_global_settings", fake_settings)
    monkeypatch.setattr(export_api, "generate_songbook_pdf", fake_pdf)

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = TestClient(app).get(
            f"/api/export/songbook/{songbook.id}/pdf",
            headers={"Authorization": f"Bearer {create_access_token()}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert [opts["double_column"] for opts in captured["per_song"]] == [False, True]
