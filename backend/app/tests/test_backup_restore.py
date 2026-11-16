"""Restoring a backup re-runs the migrations (#69)."""

from types import SimpleNamespace

import pytest
from app.api import backup as backup_api
from fastapi import HTTPException


@pytest.mark.parametrize(
    ("dump", "drops_version"),
    [
        ("CREATE TABLE songs (id uuid);\n", True),
        ("CREATE TABLE public.alembic_version (\n    version_num varchar\n);\n", False),
        ("INSERT INTO songs VALUES ('about alembic_version');\n", True),
    ],
)
async def test_restore_migrates_and_handles_pre_alembic_dumps(
    tmp_path, monkeypatch, dump, drops_version
):
    (tmp_path / "old.sql").write_text(dump)
    monkeypatch.setattr(backup_api.settings, "backup_dir", str(tmp_path))
    commands: list[list[str]] = []
    migrated: list[bool] = []

    def fake_run(command, **kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=0, stderr="")

    async def fake_init_db():
        migrated.append(True)

    monkeypatch.setattr(backup_api.subprocess, "run", fake_run)
    monkeypatch.setattr(backup_api, "init_db", fake_init_db)

    result = await backup_api.restore_backup("old.sql")

    assert result["status"] == "ok"
    assert migrated == [True]
    assert ("DROP TABLE IF EXISTS alembic_version" in commands[0]) is drops_version
    assert commands[0][-2:] == ["-f", str(tmp_path / "old.sql")]
    assert "ON_ERROR_STOP=1" in commands[0]
    assert "--single-transaction" in commands[0]


@pytest.mark.parametrize("filename", ["../etc/passwd", "/etc/passwd", "missing.sql"])
async def test_restore_rejects_paths_outside_the_backup_dir(
    tmp_path, monkeypatch, filename
):
    monkeypatch.setattr(backup_api.settings, "backup_dir", str(tmp_path / "b"))
    (tmp_path / "b").mkdir()

    with pytest.raises(HTTPException) as error:
        await backup_api.restore_backup(filename)

    assert error.value.status_code == 404
