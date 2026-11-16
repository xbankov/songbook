"""Bring the database schema to the latest Alembic revision.

Run as ``python -m app.migrate``; the API also runs it at startup.

* Empty database: ``alembic upgrade head`` creates the schema.
* Database created by the old ``init_db()`` (``create_all``), without an
  ``alembic_version`` table: the schema is checked against the baseline,
  stamped at the baseline revision, and then upgraded. No data is touched.
* Database already under Alembic: ``alembic upgrade head``.
"""

import asyncio
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from app.config import settings
from sqlalchemy import inspect, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent.parent
BASELINE_REVISION = "0001"

# The schema `init_db()` created before Alembic (revision 0001). Used only to
# check that an existing database can be safely stamped at the baseline.
BASELINE_COLUMNS: dict[str, set[str]] = {
    "settings": {
        "id",
        "transpose",
        "double_column",
        "font",
        "font_size",
        "display_mode",
    },
    "songbooks": {"id", "name", "description", "created_at", "updated_at"},
    "songs": {
        "id",
        "title",
        "artist",
        "capo",
        "key",
        "body",
        "metadata",
        "version",
        "created_at",
        "updated_at",
    },
    "tags": {"id", "name"},
    "song_tags": {"song_id", "tag_id"},
    "song_versions": {
        "id",
        "song_id",
        "version",
        "title",
        "artist",
        "capo",
        "key",
        "body",
        "created_at",
    },
    "songbook_entries": {
        "id",
        "songbook_id",
        "song_id",
        "sort_order",
        "transpose",
        "double_column",
    },
}


class BaselineMismatchError(RuntimeError):
    """An unversioned database does not match the baseline schema."""


def alembic_config(url: str | None = None) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", url or settings.database_url)
    return config


def _read_columns(connection: Connection) -> dict[str, set[str]]:
    inspector = inspect(connection)
    return {
        table: {column["name"] for column in inspector.get_columns(table)}
        for table in inspector.get_table_names()
    }


async def _existing_columns(url: str) -> dict[str, set[str]]:
    engine = create_async_engine(url, poolclass=pool.NullPool)
    try:
        async with engine.connect() as connection:
            return await connection.run_sync(_read_columns)
    finally:
        await engine.dispose()


def check_baseline(existing: dict[str, set[str]]) -> None:
    """Raise unless ``existing`` contains the full baseline schema."""
    problems = []
    for table, columns in BASELINE_COLUMNS.items():
        if table not in existing:
            problems.append(f"missing table {table}")
            continue
        missing = sorted(columns - existing[table])
        if missing:
            problems.append(f"{table} is missing {', '.join(missing)}")
    if problems:
        raise BaselineMismatchError(
            "The database has no alembic_version table and does not match the "
            f"baseline schema ({'; '.join(problems)}). Nothing was changed; "
            "fix the schema by hand, then run `alembic stamp "
            f"{BASELINE_REVISION}`."
        )


def upgrade_database(url: str | None = None) -> None:
    """Adopt an ``init_db()`` database if needed, then upgrade to head."""
    url = url or settings.database_url
    config = alembic_config(url)
    existing = asyncio.run(_existing_columns(url))
    if "alembic_version" not in existing and existing.keys() & BASELINE_COLUMNS:
        check_baseline(existing)
        logger.warning(
            "Adopting an existing database: stamping baseline revision %s",
            BASELINE_REVISION,
        )
        command.stamp(config, BASELINE_REVISION)
    command.upgrade(config, "head")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    upgrade_database()
