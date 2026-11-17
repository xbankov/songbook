"""Supermusic anti-bot stub must not become an empty song (#133)."""

from pathlib import Path

import pytest
from app.database import get_db
from app.main import app
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
        pass


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
