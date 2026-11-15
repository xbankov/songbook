from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TagOut(BaseModel):
    id: UUID
    name: str


class TagCountOut(BaseModel):
    name: str
    count: int


class SongCreate(BaseModel):
    title: str
    artist: str = "Unknown"
    capo: int = 0
    key: str | None = None
    body: str = ""
    tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict, alias="metadata_")

    @field_validator("tags")
    @classmethod
    def _tags_fit_column(cls, value: list[str]) -> list[str]:
        for tag in value:
            if len(tag) > 128:
                raise ValueError("Tag names must be 128 characters or fewer")
        return value


class SongUpdate(BaseModel):
    title: str | None = None
    artist: str | None = None
    capo: int | None = None
    key: str | None = None
    body: str | None = None
    tags: list[str] | None = None
    metadata: dict | None = Field(default=None, alias="metadata_")

    @field_validator("tags")
    @classmethod
    def _tags_fit_column(cls, value: list[str] | None) -> list[str] | None:
        for tag in value or []:
            if len(tag) > 128:
                raise ValueError("Tag names must be 128 characters or fewer")
        return value


class SongOut(BaseModel):
    id: UUID
    title: str
    artist: str
    capo: int
    key: str | None
    body: str
    metadata: dict = Field(alias="metadata_")
    version: int
    created_at: datetime
    updated_at: datetime
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags", mode="before")
    @classmethod
    def _tag_names(cls, value: Any) -> list[str]:
        if value is None:
            return []
        return [getattr(tag, "name", tag) for tag in value]

    model_config = {"from_attributes": True, "populate_by_name": True}


class SongIdsRequest(BaseModel):
    ids: list[UUID]


class SongVersionOut(BaseModel):
    id: UUID
    song_id: UUID
    version: int
    title: str
    artist: str
    capo: int
    key: str | None
    body: str
    author: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SongWithVersions(BaseModel):
    song: SongOut
    versions: list[SongVersionOut]
