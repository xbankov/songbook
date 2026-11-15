from app.database import get_db
from app.models.tag import Tag, song_tags
from app.schemas.song import TagCountOut
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=list[TagCountOut])
async def list_tags(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Tag.name, func.count(song_tags.c.song_id))
        .outerjoin(song_tags, song_tags.c.tag_id == Tag.id)
        .group_by(Tag.name)
        .order_by(Tag.name)
    )
    return [TagCountOut(name=name, count=count) for name, count in result.all()]
