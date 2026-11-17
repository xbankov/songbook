"""Supermusic anti-bot stub must not become an empty song (#133)."""

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
import requests
from app.api import search_import
from app.database import get_db
from app.main import app
from app.models.song import Song
from app.services import scraper
from app.services.auth import create_access_token
from app.services.scraper import (
    SUPERMUSIC_BLOCKED,
    SongImportError,
    import_from_url,
    parse_supermusic_html,
)
from fastapi.testclient import TestClient

FIXTURES = Path(__file__).parent / "fixtures"
# Saved 2026-11-17 from https://www.supermusic.cz/piesen.php?id=1: the page
# a non-browser client gets instead of the song.
CHALLENGE_STUB = (FIXTURES / "supermusic_challenge_stub.html").read_text()
SUPERMUSIC_URL = "https://supermusic.cz/piesen.php?id=1"


class _Session:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        pass

    async def refresh(self, obj):
        # Fill what the database would set, so the response validates.
        now = datetime.now(timezone.utc)
        for name, value in [
            ("id", uuid4()),
            ("version", 1),
            ("created_at", now),
            ("updated_at", now),
        ]:
            if getattr(obj, name, None) is None:
                setattr(obj, name, value)
        if isinstance(obj, Song):
            obj.tags = []


@pytest.fixture
def serve(monkeypatch):
    """Make fetch_url return the given HTML instead of using the network."""

    def _serve(html: str):
        monkeypatch.setattr(scraper, "fetch_url", lambda url: html)

    return _serve


@pytest.fixture
def session():
    session = _Session()

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    yield session
    app.dependency_overrides.clear()


def _post(path: str, url: str):
    return TestClient(app).post(
        path,
        params={"url": url},
        headers={"Authorization": f"Bearer {create_access_token()}"},
    )


def test_challenge_stub_is_reported_as_blocked():
    with pytest.raises(SongImportError) as error:
        parse_supermusic_html(CHALLENGE_STUB)
    assert str(error.value) == SUPERMUSIC_BLOCKED


def test_page_without_song_text_is_an_error():
    with pytest.raises(SongImportError, match="No song text"):
        parse_supermusic_html("<html><h1>Some page</h1></html>")


def test_page_with_song_text_still_imports():
    song = parse_supermusic_html("<pre>[G]Hello [C]world</pre>")
    assert "Hello" in str(song)


def test_empty_song_text_is_an_error(serve):
    serve("<pre>   </pre>")
    with pytest.raises(SongImportError, match="No song text"):
        import_from_url(SUPERMUSIC_URL)


@pytest.mark.parametrize("path", ["/api/songs/import", "/api/search/import"])
def test_import_endpoints_reject_the_stub_without_saving(serve, session, path):
    serve(CHALLENGE_STUB)

    response = _post(path, SUPERMUSIC_URL)

    assert response.status_code == 400
    assert response.json()["detail"] == SUPERMUSIC_BLOCKED
    assert session.added == []


def test_unsupported_site_is_a_clear_error(session):
    response = _post("/api/songs/import", "https://example.com/song")

    assert response.status_code == 400
    assert "Unsupported site" in response.json()["detail"]
    assert session.added == []


@pytest.mark.parametrize("path", ["/api/songs/import", "/api/search/import"])
def test_unreadable_song_text_is_a_400_not_a_500(serve, session, path):
    # "[R:]" (refrain marker) is not a chord; the chord parser raises on it.
    serve("<pre>[R:] Ahoj</pre>")

    response = _post(path, SUPERMUSIC_URL)

    assert response.status_code == 400
    assert "Could not read the song text" in response.json()["detail"]
    assert session.added == []


def _fail_with(error):
    def fetch(url):
        raise error

    return fetch


def test_download_failure_is_a_clear_error(monkeypatch):
    monkeypatch.setattr(
        scraper, "fetch_url", _fail_with(requests.ConnectionError("down"))
    )
    with pytest.raises(SongImportError, match="Could not download"):
        import_from_url(SUPERMUSIC_URL)


def test_blocked_status_suggests_paste(monkeypatch):
    response = requests.Response()
    response.status_code = 403
    monkeypatch.setattr(
        scraper, "fetch_url", _fail_with(requests.HTTPError(response=response))
    )
    with pytest.raises(SongImportError) as error:
        import_from_url(SUPERMUSIC_URL)
    assert str(error.value) == SUPERMUSIC_BLOCKED


def _ug_page(content: str) -> str:
    data = {
        "store": {
            "page": {
                "data": {
                    "tab_view": {
                        "versions": [{"song_name": "Song", "artist_name": "Artist"}],
                        "wiki_tab": {"content": content},
                    }
                }
            }
        }
    }
    payload = html.escape(json.dumps(data), quote=True)
    return f'<div class="js-store" data-content="{payload}"></div>'


class _Response:
    def __init__(self, text):
        self.text = text


@pytest.mark.parametrize("path", ["/api/songs/import", "/api/search/import"])
def test_ultimate_guitar_song_still_imports(serve, session, monkeypatch, path):
    page = _ug_page("[tab][ch]G[/ch]\nHello world[/tab]")
    serve(page)
    monkeypatch.setattr(
        search_import.requests, "get", lambda *args, **kwargs: _Response(page)
    )

    response = _post(path, "https://tabs.ultimate-guitar.com/tab/a/b-chords-1")

    assert response.status_code in (200, 201)
    if path == "/api/songs/import":
        assert "Hello world" in session.added[0].body
    else:
        assert "Hello world" in response.json()["body"]


@pytest.mark.parametrize("path", ["/api/songs/import", "/api/search/import"])
def test_ultimate_guitar_page_without_lyrics_is_rejected(
    serve, session, monkeypatch, path
):
    page = _ug_page("")
    serve(page)
    monkeypatch.setattr(
        search_import.requests, "get", lambda *args, **kwargs: _Response(page)
    )

    response = _post(path, "https://tabs.ultimate-guitar.com/tab/a/b-chords-1")

    assert response.status_code == 400
    assert session.added == []
