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
        now = datetime.now(timezone.utc)
        for obj in self.added:
            if isinstance(obj, Song):
                if obj.id is None:
                    obj.id = uuid4()
                if obj.created_at is None:
                    obj.created_at = now
                if obj.updated_at is None:
                    obj.updated_at = now
            elif isinstance(obj, SongVersion):
                if obj.id is None:
                    obj.id = uuid4()
                if obj.created_at is None:
                    obj.created_at = now

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


def _song_and_version() -> tuple[Song, SongVersion]:
    now = datetime.now(timezone.utc)
    song = Song(
        id=uuid4(),
        title="Current title",
        artist="Artist",
        capo=0,
        key="C",
        body="current body",
        metadata_={},
        version=2,
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
        capo=2,
        key="G",
        body="old body",
        created_at=now,
    )
    return song, version


def _request(path: str, db: _Session, method: str = "post"):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {create_access_token()}"}
        return getattr(client, method)(
            path,
            headers=headers,
        )
    finally:
        app.dependency_overrides.clear()


def test_favorite_version_updates_metadata():
    song, version = _song_and_version()
    db = _Session(song, version)

    response = _request(f"/api/songs/{song.id}/versions/1/favorite", db)

    assert response.status_code == 200
    data = response.json()
    metadata = data.get("metadata") or data.get("metadata_")
    assert metadata["favorite_versions"] == [1]


def test_fork_version_creates_a_new_song():
    song, version = _song_and_version()
    db = _Session(song, version)

    response = _request(f"/api/songs/{song.id}/versions/1/fork", db)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Old title (fork)"
    assert data["body"] == "old body"
    assert len(db.added) == 2
