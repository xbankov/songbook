import asyncio

import pytest
from app.database import get_db
from app.dependencies import require_auth
from app.main import app as main_app
from app.services.auth import create_access_token
from fastapi import HTTPException
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


@pytest.fixture
def client() -> TestClient:
    # TestClient is used without a context manager, so the DB lifespan does not
    # run; anonymous requests are rejected before any DB access.
    return TestClient(main_app)


def auth_header() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token()}"}


@pytest.mark.parametrize("path", PROTECTED_GET_PATHS)
def test_protected_get_requires_auth(client: TestClient, path: str):
    assert client.get(path).status_code == 401


def test_protected_post_requires_auth(client: TestClient):
    response = client.post(
        "/api/songs/import", params={"url": "https://example.com/song"}
    )
    assert response.status_code == 401


def test_health_and_login_stay_public(client: TestClient):
    assert client.get("/api/health").status_code == 200
    # 401 comes from the login handler, not from the auth dependency.
    response = client.post(
        "/api/auth/login", json={"username": "wrong", "password": "wrong"}
    )
    assert response.status_code == 401


def test_require_auth_accepts_a_valid_token():
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=create_access_token()
    )
    assert asyncio.run(require_auth(credentials)) is None


def test_require_auth_rejects_missing_credentials():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(require_auth(None))
    assert exc.value.status_code == 401


def test_require_auth_rejects_an_invalid_token():
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="not-a-token"
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(require_auth(credentials))
    assert exc.value.status_code == 401


class _FakeScalars:
    def all(self):
        return []


class _FakeResult:
    def scalars(self):
        return _FakeScalars()


class _FakeSession:
    async def execute(self, *args, **kwargs):
        return _FakeResult()


async def _override_get_db():
    yield _FakeSession()


def test_authenticated_request_succeeds():
    main_app.dependency_overrides[get_db] = _override_get_db
    try:
        response = TestClient(main_app).get("/api/songs", headers=auth_header())
        assert response.status_code == 200
        assert response.json() == []
    finally:
        main_app.dependency_overrides.clear()
