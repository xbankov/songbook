"""Title, artist, capo and key live in song fields, not in the body (#37)."""

from datetime import datetime, timezone
from uuid import uuid4

from app.database import get_db
from app.main import app
from app.models.song import Song, SongVersion
from app.services.auth import create_access_token
from app.services.converters import (
    absorb_chordpro_metadata,
    ensure_chordpro_metadata,
    song_model_from_fields,
    split_chordpro_metadata,
)
from fastapi.testclient import TestClient

STALE_BODY = "\n".join(
    [
        "{title: Old Title}",
        "{artist: Old Artist}",
        "{capo: 3}",
        "{key: G}",
        "{start_of_verse}",
        "[G]Hello [C]world",
        "{end_of_verse}",
    ]
)


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.value


class _Session:
    def __init__(self, results: list | None = None):
        self.results = results or []
        self.added: list = []

    async def execute(self, *args, **kwargs):
        return _Result(self.results.pop(0))

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        now = datetime.now(timezone.utc)
        for obj in self.added:
            if obj.id is None:
                obj.id = uuid4()
            if obj.created_at is None:
                obj.created_at = now
            if isinstance(obj, Song) and obj.updated_at is None:
                obj.updated_at = now
            if isinstance(obj, Song) and obj.version is None:
                obj.version = 1

    async def refresh(self, obj):
        pass


def _song(**overrides) -> Song:
    now = datetime.now(timezone.utc)
    values = dict(
        id=uuid4(),
        title="New Title",
        artist="New Artist",
        capo=0,
        key="G",
        body=STALE_BODY,
        metadata_={},
        version=1,
        created_at=now,
        updated_at=now,
    )
    values.update(overrides)
    song = Song(**values)
    song.tags = []
    return song


def _call(db: _Session, method: str, url: str, **kwargs):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        return TestClient(app).request(
            method,
            url,
            headers={"Authorization": f"Bearer {create_access_token()}"},
            **kwargs,
        )
    finally:
        app.dependency_overrides.clear()


def test_split_removes_metadata_lines_and_keeps_other_directives():
    body = "\n".join(
        [
            "{ Title : Song }",
            "{ARTIST: Band}",
            "",
            "{comment: intro}",
            "{start_of_chorus}",
            "[G]La",
            "{end_of_chorus}",
        ]
    )

    clean, values = split_chordpro_metadata(body)

    assert values == {"title": "Song", "artist": "Band"}
    assert clean == "{comment: intro}\n{start_of_chorus}\n[G]La\n{end_of_chorus}"


def test_absorb_keeps_provided_fields_and_fills_missing_ones():
    clean, fields = absorb_chordpro_metadata(
        STALE_BODY, {"title": "Mine", "artist": None, "capo": None, "key": None}
    )

    assert "{" + "title" not in clean
    assert fields == {"title": "Mine", "artist": "Old Artist", "capo": 3, "key": "G"}


def test_absorb_ignores_an_invalid_capo_tag():
    _, fields = absorb_chordpro_metadata("{capo: two}\n[G]La", {"capo": None})

    assert fields == {"capo": None}


def test_song_model_prefers_fields_over_stale_body_tags():
    model = song_model_from_fields(STALE_BODY, "New Title", "New Artist", 0, "A")

    assert (model.title, model.artist, model.key) == ("New Title", "New Artist", "A")
    # An empty field still falls back to an old body tag.
    assert model.capo == 3


def test_ensure_metadata_writes_each_tag_once_from_the_fields():
    out = ensure_chordpro_metadata(STALE_BODY, "New Title", "New Artist", 0, "A")

    assert out.splitlines()[:3] == [
        "{title: New Title}",
        "{artist: New Artist}",
        "{key: A}",
    ]
    assert "Old" not in out
    assert out.count("{key:") == 1


def test_create_strips_tags_and_uses_them_only_for_missing_fields():
    db = _Session()

    response = _call(
        db,
        "POST",
        "/api/songs",
        json={"title": "Typed Title", "artist": "", "body": STALE_BODY},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Typed Title"
    assert data["artist"] == "Old Artist"
    assert (data["capo"], data["key"]) == (3, "G")
    assert data["body"] == "{start_of_verse}\n[G]Hello [C]world\n{end_of_verse}"


def test_update_strips_tags_and_keeps_the_sent_fields():
    song = _song()
    db = _Session([song])

    response = _call(
        db,
        "PUT",
        f"/api/songs/{song.id}",
        json={
            "title": "Renamed",
            "artist": "New Artist",
            "capo": 0,
            "body": STALE_BODY,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert (data["title"], data["artist"], data["capo"]) == ("Renamed", "New Artist", 0)
    # The request left the key out, so the body tag fills it.
    assert data["key"] == "G"
    assert "{title" not in data["body"] and "{key" not in data["body"]
    version = next(obj for obj in db.added if isinstance(obj, SongVersion))
    assert version.title == "Renamed" and version.body == data["body"]


def test_bulk_export_uses_the_song_fields_not_stale_body_tags():
    db = _Session([[_song()]])

    response = _call(db, "GET", "/api/songs/export/bulk?format=chordpro")

    assert response.status_code == 200
    assert "{title: New Title}" in response.text
    assert "{artist: New Artist}" in response.text
    assert "Old Title" not in response.text


def test_bulk_export_text_uses_the_song_fields():
    db = _Session([[_song()]])

    response = _call(db, "GET", "/api/songs/export/bulk?format=text")

    assert response.status_code == 200
    assert response.text.startswith("New Title - New Artist")


def test_transpose_updates_the_key_field_and_keeps_tags_out_of_the_body():
    song = _song(body="[G]Hello [C]world", key="G")
    db = _Session([song])

    response = _call(db, "GET", f"/api/songs/{song.id}/transpose?interval=2")

    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "A"
    assert "[A]Hello" in data["body"] and "[D]world" in data["body"]
    assert "{" not in data["body"]


def test_restore_strips_tags_from_an_old_version_body():
    song = _song(body="[C]current", version=2)
    old = SongVersion(
        id=uuid4(),
        song_id=song.id,
        version=1,
        title="Old Title",
        artist="Old Artist",
        capo=3,
        key="G",
        body=STALE_BODY,
        created_at=datetime.now(timezone.utc),
    )
    db = _Session([song, old])

    response = _call(db, "POST", f"/api/songs/{song.id}/versions/1/restore")

    assert response.status_code == 200
    data = response.json()
    assert (data["title"], data["capo"], data["key"]) == ("Old Title", 3, "G")
    assert data["body"] == "{start_of_verse}\n[G]Hello [C]world\n{end_of_verse}"
