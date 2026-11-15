import asyncio
import uuid

from app.models.settings import Settings
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# Fixed id so two concurrent first requests cannot create two settings rows.
SETTINGS_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def get_or_create_settings(db: AsyncSession) -> Settings:
    result = await db.execute(select(Settings).limit(1))
    settings = result.scalar_one_or_none()
    if settings is not None:
        return settings

    settings = Settings(id=SETTINGS_ID)
    db.add(settings)
    try:
        await db.flush()
    except IntegrityError:
        # Another request created the singleton first. Roll back and read it.
        await db.rollback()
        for _ in range(3):
            result = await db.execute(select(Settings).limit(1))
            existing = result.scalar_one_or_none()
            if existing is not None:
                return existing
            await asyncio.sleep(0.05)
        raise
    await db.refresh(settings)
    return settings
