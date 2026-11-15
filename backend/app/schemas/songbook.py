from datetime import datetime
from uuid import UUID

from app.schemas.song import SongOut
from pydantic import BaseModel, Field


class SongbookCreate(BaseModel):
    name: str
    description: str = ""


class SongbookUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


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
    transpose: int
    double_column: int
    song: SongOut | None = None

    model_config = {"from_attributes": True}


class SongbookEntryUpdate(BaseModel):
    sort_order: int | None = None
    transpose: int | None = Field(None, ge=-11, le=11)
    double_column: bool | None = None


class SongbookOrderUpdate(BaseModel):
    entry_ids: list[UUID]


class SongbookDetailOut(SongbookOut):
    entries: list[SongbookEntryOut] = []
