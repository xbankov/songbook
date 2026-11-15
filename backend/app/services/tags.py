from app.models.tag import Tag
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def clean_tag_names(names: list[str] | None) -> list[str]:
    return sorted({name.strip() for name in (names or []) if name and name.strip()})


async def resolve_tags(db: AsyncSession, names: list[str] | None) -> list[Tag]:
    cleaned = clean_tag_names(names)
    if not cleaned:
        return []

    result = await db.execute(select(Tag).where(Tag.name.in_(cleaned)))
    existing = {tag.name: tag for tag in result.scalars().all()}
    tags: list[Tag] = []
    for name in cleaned:
        tag = existing.get(name)
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
        tags.append(tag)
    await db.flush()
    return tags
