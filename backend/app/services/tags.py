from app.models.tag import Tag
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


def clean_tag_names(names: list[str] | None) -> list[str]:
    cleaned: set[str] = set()
    for raw in names or []:
        if not raw:
            continue
        name = raw.strip()
        if not name:
            continue
        # Difficulty and genre filters compare lowercased names.
        if name.lower().startswith(("difficulty:", "genre:")):
            name = name.lower()
        cleaned.add(name)
    return sorted(cleaned)


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
            try:
                # A savepoint keeps the outer song transaction alive if another
                # request inserted the same tag first.
                async with db.begin_nested():
                    tag = Tag(name=name)
                    db.add(tag)
                    await db.flush()
            except IntegrityError:
                found = await db.execute(select(Tag).where(Tag.name == name))
                tag = found.scalar_one()
            existing[name] = tag
        tags.append(tag)
    return tags
