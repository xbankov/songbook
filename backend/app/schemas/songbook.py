from datetime import date as Date
from datetime import datetime
from uuid import UUID

from app.schemas.song import SongOut
from pydantic import BaseModel, Field, field_validator


class SongbookMetadata(BaseModel):
    author: str | None = Field(None, max_length=256)
    date: Date | None = None
    genre: str | None = Field(None, max_length=128)
    difficulty: str | None = Field(None, max_length=64)

    @field_validator("author", "genre", "difficulty")
    @classmethod
    def _blank_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class SongbookCreate(SongbookMetadata):
    name: str
    description: str = ""


class SongbookUpdate(SongbookMetadata):
    name: str | None = None
    description: str | None = None


class SongbookOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    author: str | None = None
    date: Date | None = None
    genre: str | None = None
    difficulty: str | None = None
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
