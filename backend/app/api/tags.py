from app.database import get_db
from app.models.tag import Tag
from app.schemas.song import TagCountOut
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=list[TagCountOut])
async def list_tags(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tag).order_by(Tag.name))
    return [
        TagCountOut(name=tag.name, count=len(tag.songs))
        for tag in result.scalars().all()
    ]
