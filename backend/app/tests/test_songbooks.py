from datetime import datetime, timezone
from uuid import uuid4

from app.database import get_db
from app.main import app
from app.models.song import Song
from app.models.songbook import Songbook, SongbookEntry
from app.services.auth import create_access_token
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


def test_reorder_songbook_assigns_consecutive_positions():
    now = datetime.now(timezone.utc)
    songbook = Songbook(
        id=uuid4(),
        name="Book",
        description="",
        created_at=now,
        updated_at=now,
    )
    first = SongbookEntry(
        id=uuid4(),
        songbook_id=songbook.id,
        song_id=uuid4(),
        sort_order=0,
        transpose=0,
        double_column=0,
    )
    second = SongbookEntry(
        id=uuid4(),
        songbook_id=songbook.id,
        song_id=uuid4(),
        sort_order=1,
        transpose=0,
        double_column=0,
    )
    songbook.entries = [first, second]
    db = _Session(songbook)

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = TestClient(app).put(
            f"/api/songbooks/{songbook.id}/order",
            json={"entry_ids": [str(second.id), str(first.id)]},
            headers={"Authorization": f"Bearer {create_access_token()}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    positions = {
        entry["id"]: entry["sort_order"] for entry in response.json()["entries"]
    }
    assert positions[str(second.id)] == 0
    assert positions[str(first.id)] == 1


def test_songbook_chordpro_export_contains_entry_song():
    now = datetime.now(timezone.utc)
    songbook = Songbook(
        id=uuid4(),
        name="Book",
        description="",
        created_at=now,
        updated_at=now,
    )
    song = Song(
        id=uuid4(),
        title="Exported Song",
        artist="Artist",
        capo=0,
        key="G",
        body="{title: Exported Song}\n{artist: Artist}\n[G]Hello",
        metadata_={},
        version=1,
        created_at=now,
        updated_at=now,
    )
    song.tags = []
    entry = SongbookEntry(
        id=uuid4(),
        songbook_id=songbook.id,
        song_id=song.id,
        sort_order=0,
        transpose=0,
        double_column=0,
    )
    entry.song = song
    songbook.entries = [entry]
    db = _Session(songbook)

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = TestClient(app).get(
            f"/api/export/songbook/{songbook.id}/chordpro",
            headers={"Authorization": f"Bearer {create_access_token()}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "Exported Song" in response.text
    assert "[G]Hello" in response.text
    assert ".cho" in response.headers["content-disposition"]
