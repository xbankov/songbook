import pytest
from app.services.tags import clean_tag_names, resolve_tags


def test_clean_tag_names_trims_dedupes_and_sorts():
    assert clean_tag_names(
        [" genre:bluegrass ", "", "difficulty:easy", "difficulty:easy", None]
    ) == [
        "difficulty:easy",
        "genre:bluegrass",
    ]


class _FakeScalars:
    def all(self):
        return []


class _FakeResult:
    def scalars(self):
        return _FakeScalars()


class _FakeSession:
    def __init__(self):
        self.added = []

    async def execute(self, *args, **kwargs):
        return _FakeResult()

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        pass


def test_resolve_tags_creates_missing_tags_once():
    import asyncio

    db = _FakeSession()
    tags = asyncio.run(resolve_tags(db, ["difficulty:easy", "difficulty:easy"]))
    assert [tag.name for tag in tags] == ["difficulty:easy"]
    assert [tag.name for tag in db.added] == ["difficulty:easy"]


def test_resolve_tags_with_no_names_returns_empty():
    import asyncio

    db = _FakeSession()
    assert asyncio.run(resolve_tags(db, [])) == []
    assert db.added == []
