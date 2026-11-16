"""YouTube link per song (#25)."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from app.database import get_db
from app.main import app
from app.models.song import Song
from app.services.auth import create_access_token
from app.services.youtube import canonical_youtube_url, youtube_video_id
from fastapi.testclient import TestClient

VIDEO = "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.youtube.com/watch?v={VIDEO}",
        f"https://youtube.com/watch?list=PL1&v={VIDEO}&t=42s",
        f"http://m.youtube.com/watch?v={VIDEO}",
        f"https://music.youtube.com/watch?v={VIDEO}",
        f"https://youtu.be/{VIDEO}?t=10",
        f"youtu.be/{VIDEO}",
        f"https://www.youtube.com/shorts/{VIDEO}",
        f"https://www.youtube.com/embed/{VIDEO}",
        f"https://www.youtube-nocookie.com/embed/{VIDEO}",
        f"  https://www.youtube.com/live/{VIDEO}  ",
        f"https://www.youtube.com/watch/?v={VIDEO}",
    ],
)
def test_video_id_from_common_url_forms(url):
    assert youtube_video_id(url) == VIDEO


@pytest.mark.parametrize(
    "url",
    [
        "https://vimeo.com/123456",
        f"https://evil.example/watch?v={VIDEO}",
        f"https://youtube.com.evil.example/watch?v={VIDEO}",
        "https://www.youtube.com/watch?v=short",
        f"https://www.youtube.com/watch?v={VIDEO}%0A",
        "https://www.youtube.com/channel/UC123",
        f"javascript:alert(1)//youtu.be/{VIDEO}",
        "",
    ],
)
def test_non_youtube_or_malformed_urls_are_rejected(url):
    assert youtube_video_id(url) is None


def test_canonical_url():
    assert (
        canonical_youtube_url(f"https://youtu.be/{VIDEO}")
        == f"https://www.youtube.com/watch?v={VIDEO}"
    )


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _Session:
    def __init__(self, song):
        self.song = song

    async def execute(self, *args, **kwargs):
        return _Result(self.song)

    async def flush(self):
        pass

    async def refresh(self, obj):
        pass


def _song(metadata: dict) -> Song:
    now = datetime.now(timezone.utc)
    song = Song(
        id=uuid4(),
        title="Song",
        artist="Artist",
        capo=0,
        key=None,
        body="[G]la",
        metadata_=metadata,
        version=3,
        created_at=now,
        updated_at=now,
    )
    song.tags = []
    return song


def _put(song: Song, url):
    async def override_get_db():
        yield _Session(song)

    app.dependency_overrides[get_db] = override_get_db
    try:
        return TestClient(app).put(
            f"/api/songs/{song.id}/youtube",
            json={"url": url},
            headers={"Authorization": f"Bearer {create_access_token()}"},
        )
    finally:
        app.dependency_overrides.clear()


def test_set_youtube_link_keeps_other_metadata_and_version():
    song = _song({"audio_file": "a.webm"})

    response = _put(song, f"https://youtu.be/{VIDEO}")

    assert response.status_code == 200
    body = response.json()
    assert body["metadata"] == {
        "audio_file": "a.webm",
        "youtube_url": f"https://www.youtube.com/watch?v={VIDEO}",
    }
    assert body["version"] == 3


@pytest.mark.parametrize("url", [None, "", "   "])
def test_clear_youtube_link(url):
    song = _song({"youtube_url": "https://www.youtube.com/watch?v=x", "a": 1})

    response = _put(song, url)

    assert response.status_code == 200
    assert response.json()["metadata"] == {"a": 1}


def test_reject_non_youtube_link():
    song = _song({})

    response = _put(song, "https://vimeo.com/1")

    assert response.status_code == 422
    assert song.metadata_ == {}
