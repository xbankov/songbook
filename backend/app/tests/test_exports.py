from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.database import get_db
from app.main import app
from app.models.song import Song
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
            _ListResult([first, second]),
            _OneResult(SimpleNamespace(transpose=0)),
        ]
    )

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = TestClient(app).get(
            "/api/songs/export/selected",
            params=[("ids", str(first.id)), ("ids", str(second.id))],
            headers={"Authorization": f"Bearer {create_access_token()}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.text.index("First Song") < response.text.index("Second Song")
    assert "selected.cho" in response.headers["content-disposition"]
