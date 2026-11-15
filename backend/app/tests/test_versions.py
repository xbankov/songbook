from datetime import datetime, timezone
from uuid import uuid4

from app.database import get_db
from app.main import app
from app.models.song import Song, SongVersion
from app.services.auth import create_access_token
from fastapi.testclient import TestClient


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _Session:
    def __init__(self, song: Song, version: SongVersion):
        self._results = [song, version]
        self.added = []

    async def execute(self, *args, **kwargs):
        return _Result(self._results.pop(0))

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        pass

    async def refresh(self, obj):
        pass


def test_restore_version_restores_content_as_a_new_version():
    now = datetime.now(timezone.utc)
    song = Song(
        id=uuid4(),
        title="New title",
        artist="Artist",
        capo=1,
        key="C",
        body="new body",
        metadata_={},
        version=3,
        created_at=now,
        updated_at=now,
    )
    song.tags = []
    version = SongVersion(
        id=uuid4(),
        song_id=song.id,
        version=1,
        title="Old title",
        artist="Old artist",
        capo=0,
        key="G",
        body="old body",
        created_at=now,
    )
    db = _Session(song, version)

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = TestClient(app).post(
            f"/api/songs/{song.id}/versions/1/restore",
            headers={"Authorization": f"Bearer {create_access_token()}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Old title"
    assert body["artist"] == "Old artist"
    assert body["key"] == "G"
    assert body["body"] == "old body"
    assert body["version"] == 4
    assert db.added[0].version == 4
    assert db.added[0].body == "old body"
