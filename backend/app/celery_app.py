import logging
import os
import subprocess
from datetime import datetime, timezone

from app.config import settings
from celery import Celery

logger = logging.getLogger(__name__)

celery_app = Celery(
    "songbook",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "daily-backup": {
            "task": "app.celery_app.daily_backup",
            "schedule": 86400.0,
        },
    },
)


@celery_app.task
def daily_backup():
    os.makedirs(settings.backup_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"songbook_auto_{timestamp}.sql"
    filepath = os.path.join(settings.backup_dir, filename)
    try:
        url = settings.database_url_sync
        result = subprocess.run(
            ["pg_dump", url, "--clean", "--if-exists", "-f", filepath],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            logger.error(f"Auto backup failed: {result.stderr}")
            return {"status": "error", "error": result.stderr}
        logger.info(f"Auto backup created: {filepath}")

        # Cleanup old backups
        now = datetime.now(timezone.utc).timestamp()
        for f in os.listdir(settings.backup_dir):
            fp = os.path.join(settings.backup_dir, f)
            if os.path.isfile(fp) and f.endswith(".sql"):
                age_days = (now - os.path.getmtime(fp)) / 86400
                if age_days > settings.backup_retention_days:
                    os.remove(fp)
                    logger.info(f"Removed old backup: {f}")
        return {"status": "ok", "filename": filename}
    except Exception as e:
        logger.error(f"Auto backup failed: {e}")
        return {"status": "error", "error": str(e)}
