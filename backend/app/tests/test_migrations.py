"""Alembic migration tests (#69).

The database tests need a disposable PostgreSQL database; set
MIGRATION_TEST_DATABASE_URL (asyncpg URL) to run them. Every test drops and
recreates the public schema, so never point it at a real database.
"""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from app.database import Base
from app.migrate import (
    BASELINE_COLUMNS,
    BASELINE_REVISION,
    BaselineMismatchError,
    alembic_config,
    check_baseline,
    upgrade_database,
)
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.environ.get("MIGRATION_TEST_DATABASE_URL")
needs_postgres = pytest.mark.skipif(
    not DATABASE_URL, reason="MIGRATION_TEST_DATABASE_URL is not set"
)


def _run(sync_fn):
    """Run ``sync_fn(connection)`` on a fresh connection and commit."""

    async def go():
        engine = create_async_engine(DATABASE_URL, poolclass=pool.NullPool)
        try:
            async with engine.begin() as connection:
                return await connection.run_sync(sync_fn)
        finally:
            await engine.dispose()

    return asyncio.run(go())


def _reset_schema(connection) -> None:
    connection.execute(text("DROP SCHEMA public CASCADE"))
    connection.execute(text("CREATE SCHEMA public"))


def _tables(connection) -> set[str]:
    return set(
        connection.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        ).scalars()
    )


def _current_revision(connection) -> str | None:
    return MigrationContext.configure(connection).get_current_revision()


def _head() -> str:
    return ScriptDirectory.from_config(alembic_config(DATABASE_URL)).get_current_head()


@pytest.fixture
def clean_db():
    _run(_reset_schema)
    yield
    _run(_reset_schema)


def test_check_baseline_accepts_full_schema_with_extra_columns():
    existing = {table: set(cols) for table, cols in BASELINE_COLUMNS.items()}
    existing["songs"].add("extra")
    check_baseline(existing)


def test_check_baseline_rejects_missing_table_and_column():
    existing = {table: set(cols) for table, cols in BASELINE_COLUMNS.items()}
    del existing["tags"]
    existing["songs"].discard("capo")
    with pytest.raises(BaselineMismatchError) as error:
        check_baseline(existing)
    assert "missing table tags" in str(error.value)
    assert "songs is missing capo" in str(error.value)


@needs_postgres
def test_upgrade_creates_schema_matching_models(clean_db):
    upgrade_database(DATABASE_URL)

    assert _run(_current_revision) == _head()
    assert set(BASELINE_COLUMNS) <= _run(_tables)

    def diff(connection):
        return compare_metadata(MigrationContext.configure(connection), Base.metadata)

    # The models and the migrations must describe the same schema.
    assert _run(diff) == []


@needs_postgres
def test_downgrade_base_removes_schema(clean_db):
    upgrade_database(DATABASE_URL)
    command.downgrade(alembic_config(DATABASE_URL), "base")

    assert _run(_tables) == {"alembic_version"}
    assert _run(_current_revision) is None


@needs_postgres
def test_existing_init_db_database_is_adopted_without_data_loss(clean_db):
    song_id = uuid4()
    create_unversioned_baseline()

    def insert_song(connection):
        connection.execute(
            text(
                "INSERT INTO songs (id, title, artist, capo, body, metadata, "
                "version, created_at, updated_at) VALUES (:id, 'Kept', 'Me', 0, "
                "'[G]la', '{}', 1, now(), now())"
            ),
            {"id": song_id},
        )

    _run(insert_song)
    assert "alembic_version" not in _run(_tables)

    upgrade_database(DATABASE_URL)

    assert _run(_current_revision) == _head()

    def titles(connection):
        return list(connection.execute(text("SELECT title FROM songs")).scalars())

    assert _run(titles) == ["Kept"]


@needs_postgres
def test_mismatched_unversioned_database_is_left_untouched(clean_db):
    def partial_schema(connection):
        connection.execute(text("CREATE TABLE songs (id uuid PRIMARY KEY)"))

    _run(partial_schema)

    with pytest.raises(BaselineMismatchError):
        upgrade_database(DATABASE_URL)

    assert _run(_tables) == {"songs"}


def create_unversioned_baseline() -> None:
    """Create the baseline schema as an old init_db() left it: no alembic_version."""
    command.upgrade(alembic_config(DATABASE_URL), BASELINE_REVISION)
    _run(lambda connection: connection.execute(text("DROP TABLE alembic_version")))


def test_alembic_config_keeps_percent_escapes_in_url():
    url = "postgresql+asyncpg://songbook:p%40ss%25word@db:5432/songbook"

    assert alembic_config(url).get_main_option("sqlalchemy.url") == url


@needs_postgres
def test_concurrent_migrations_are_serialised(clean_db):
    create_unversioned_baseline()

    with ThreadPoolExecutor(max_workers=3) as pool_:
        futures = [pool_.submit(upgrade_database, DATABASE_URL) for _ in range(3)]
        for future in futures:
            future.result()

    assert _run(_current_revision) == _head()
