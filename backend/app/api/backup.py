import logging
import os
import subprocess
from datetime import datetime, timezone

from app.config import settings
from app.database import init_db
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.post("/create")
async def create_backup():
    os.makedirs(settings.backup_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"songbook_backup_{timestamp}.sql"
    filepath = os.path.join(settings.backup_dir, filename)

    try:
        # Parse the sync URL to extract components
        url = settings.database_url_sync
        # postgresql://user:pass@host:port/db
        result = subprocess.run(
            ["pg_dump", url, "--clean", "--if-exists", "-f", filepath],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            logger.error(f"pg_dump failed: {result.stderr}")
            raise HTTPException(
                status_code=500, detail=f"Backup failed: {result.stderr}"
            )
        logger.info(f"Backup created: {filepath}")
        return {
            "filename": filename,
            "size": os.path.getsize(filepath),
            "created_at": timestamp,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="pg_dump not found on server")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Backup timed out")


@router.get("/list")
async def list_backups():
    os.makedirs(settings.backup_dir, exist_ok=True)
    backups = []
    for f in sorted(os.listdir(settings.backup_dir), reverse=True):
        if f.endswith(".sql"):
            path = os.path.join(settings.backup_dir, f)
            backups.append(
                {
                    "filename": f,
                    "size": os.path.getsize(path),
                    "created_at": datetime.fromtimestamp(
                        os.path.getmtime(path), tz=timezone.utc
                    ).isoformat(),
                }
            )
    return backups


def _backup_path(filename: str) -> str:
    """Path of an existing .sql backup directly inside BACKUP_DIR, or 404.

    The path is built from the directory listing, never from the request, so
    `../`, absolute paths and symlinks out of the directory cannot match.
    """
    backup_dir = os.path.realpath(settings.backup_dir)
    names = os.listdir(backup_dir) if os.path.isdir(backup_dir) else []
    match = next(
        (name for name in names if name == filename and name.endswith(".sql")), None
    )
    if match is None:
        raise HTTPException(status_code=404, detail="Backup not found")
    filepath = os.path.realpath(os.path.join(backup_dir, match))
    if os.path.dirname(filepath) != backup_dir or not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="Backup not found")
    return filepath


@router.get("/download/{filename}")
async def download_backup(filename: str):
    filepath = _backup_path(filename)
    with open(filepath, "rb") as f:
        content = f.read()
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _dump_has_alembic_version(filepath: str) -> bool:
    with open(filepath, encoding="utf-8", errors="replace") as dump:
        return any(
            line.startswith("CREATE TABLE public.alembic_version") for line in dump
        )


@router.post("/restore")
async def restore_backup(filename: str):
    filepath = _backup_path(filename)
    try:
        url = settings.database_url_sync
        # One transaction that stops at the first error: a failed restore
        # leaves the database as it was.
        command = ["psql", url, "-v", "ON_ERROR_STOP=1", "--single-transaction"]
        if not _dump_has_alembic_version(filepath):
            # A pre-Alembic dump does not replace alembic_version; drop it so
            # the migration below re-adopts the restored schema (#69).
            command += ["-c", "DROP TABLE IF EXISTS alembic_version"]
        result = subprocess.run(
            command + ["-f", filepath],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            logger.error(f"Restore failed: {result.stderr}")
            raise HTTPException(
                status_code=500, detail=f"Restore failed: {result.stderr}"
            )
        # Bring an older backup's schema up to the current revision.
        await init_db()
        return {"status": "ok", "message": f"Restored from {filename}"}
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="psql not found on server")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Restore timed out")
