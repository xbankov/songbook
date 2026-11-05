from datetime import datetime
from uuid import UUID

from app.schemas.song import SongOut
from pydantic import BaseModel


class SongbookCreate(BaseModel):
    name: str
    description: str = ""


class SongbookOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SongbookEntryOut(BaseModel):
    id: UUID
    song_id: UUID
    songbook_id: UUID
    sort_order: int
    song: SongOut | None = None

    model_config = {"from_attributes": True}


class SongbookEntryUpdate(BaseModel):
    sort_order: int | None = None


class SongbookDetailOut(SongbookOut):
    entries: list[SongbookEntryOut] = []
