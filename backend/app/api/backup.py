import logging
import os
import subprocess
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.config import settings

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
            raise HTTPException(status_code=500, detail=f"Backup failed: {result.stderr}")
        logger.info(f"Backup created: {filepath}")
        return {"filename": filename, "size": os.path.getsize(filepath), "created_at": timestamp}
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
            backups.append({
                "filename": f,
                "size": os.path.getsize(path),
                "created_at": datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc).isoformat(),
            })
    return backups


@router.get("/download/{filename}")
async def download_backup(filename: str):
    filepath = os.path.join(settings.backup_dir, filename)
    if not os.path.exists(filepath) or ".." in filename:
        raise HTTPException(status_code=404, detail="Backup not found")
    with open(filepath, "rb") as f:
        content = f.read()
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/restore")
async def restore_backup(filename: str):
    filepath = os.path.join(settings.backup_dir, filename)
    if not os.path.exists(filepath) or ".." in filename:
        raise HTTPException(status_code=404, detail="Backup not found")
    try:
        url = settings.database_url_sync
        result = subprocess.run(
            ["psql", url, "-f", filepath],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            logger.error(f"Restore failed: {result.stderr}")
            raise HTTPException(status_code=500, detail=f"Restore failed: {result.stderr}")
        return {"status": "ok", "message": f"Restored from {filename}"}
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="psql not found on server")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Restore timed out")
