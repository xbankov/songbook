from app.database import get_db
from app.models.settings import Settings
from app.schemas.settings import SettingsOut, SettingsUpdate
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/settings", tags=["settings"])


async def get_or_create_settings(db: AsyncSession) -> Settings:
    result = await db.execute(select(Settings).limit(1))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = Settings()
        db.add(settings)
        await db.flush()
        await db.refresh(settings)
    return settings


@router.get("", response_model=SettingsOut)
async def get_settings(db: AsyncSession = Depends(get_db)):
    return await get_or_create_settings(db)


@router.put("", response_model=SettingsOut)
async def update_settings(body: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    settings = await get_or_create_settings(db)
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "double_column":
            value = 1 if value else 0
        setattr(settings, field, value)
    await db.flush()
    await db.refresh(settings)
    return settings
