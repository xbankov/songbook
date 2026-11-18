"""Server chord shapes for the song-view popover (#142)."""

import pytest
from app.main import app
from app.services.auth import create_access_token
from app.services.chord_shapes import chord_shape
from app.services.music_theory import Chord
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    ("name", "frets"),
    [
        ("G", [3, 2, 0, 0, 0, 3]),
        ("C", [0, 3, 2, 0, 1, 0]),
        ("Am", [0, 0, 2, 2, 1, 0]),
        ("E7", [0, 2, 0, 1, 0, 0]),
        ("G/B", [3, 2, 0, 0, 0, 3]),
    ],
)
def test_chord_shape_uses_open_positions(name, frets):
    assert chord_shape(Chord.parse(name)) == frets


def test_chord_shape_unknown_quality_has_no_diagram():
    assert chord_shape(Chord.parse("Cxyz")) is None


def _get(chord: str, token: bool = True):
    headers = {"Authorization": f"Bearer {create_access_token()}"} if token else {}
    return TestClient(app).get("/api/chords", params={"chord": chord}, headers=headers)


def test_endpoint_returns_the_server_shape():
    response = _get("G/B")

    assert response.status_code == 200
    assert response.json() == {"name": "G/B", "frets": [3, 2, 0, 0, 0, 3]}


def test_endpoint_reports_unknown_chords():
    assert _get("Cxyz").status_code == 404
    assert _get("not-a-chord").status_code == 400


def test_endpoint_requires_auth():
    assert _get("G", token=False).status_code == 401
