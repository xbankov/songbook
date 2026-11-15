import asyncio

import pytest
from app.api import artists, auth, backup, export, search_import
from app.api import settings as settings_router
from app.api import songbooks, songs
from app.dependencies import require_auth
from app.services.auth import create_access_token
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

PROTECTED_GET_PATHS = [
    "/api/songs",
    "/api/songs/00000000-0000-0000-0000-000000000000/versions",
    "/api/songbooks",
    "/api/artists",
    "/api/settings",
    "/api/backup/list",
    "/api/search?q=ab",
    "/api/export/song/00000000-0000-0000-0000-000000000000/pdf",
    "/api/export/songbook/00000000-0000-0000-0000-000000000000/pdf",
]


def protected_app() -> FastAPI:
    app = FastAPI()
    for router in (
        songs.router,
        songbooks.router,
        artists.router,
        export.router,
        search_import.router,
        backup.router,
        settings_router.router,
    ):
        app.include_router(router, dependencies=[Depends(require_auth)])
    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(protected_app())


@pytest.mark.parametrize("path", PROTECTED_GET_PATHS)
def test_protected_get_requires_auth(client: TestClient, path: str):
    assert client.get(path).status_code == 401


def test_protected_post_requires_auth(client: TestClient):
    response = client.post(
        "/api/songs/import", params={"url": "https://example.com/song"}
    )
    assert response.status_code == 401


def test_login_stays_public():
    app = FastAPI()
    app.include_router(auth.router)
    client = TestClient(app)

    response = client.post(
        "/api/auth/login", json={"username": "wrong", "password": "wrong"}
    )
    # 401 comes from the login handler, not from the auth dependency.
    assert response.status_code == 401


def test_require_auth_accepts_a_valid_token():
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=create_access_token()
    )
    assert asyncio.run(require_auth(credentials)) is None


def test_require_auth_rejects_an_invalid_token():
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="not-a-token"
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(require_auth(credentials))
    assert exc.value.status_code == 401


def test_main_app_wires_auth_and_keeps_health_public():
    from app.main import app as main_app

    client = TestClient(main_app)
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/songs").status_code == 401
    assert client.get("/api/settings").status_code == 401
