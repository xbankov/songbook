from datetime import datetime
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


class SongUpdate(BaseModel):
    title: str | None = None
    artist: str | None = None
    capo: int | None = None
    key: str | None = None
    body: str | None = None
    tags: list[str] | None = None
    metadata: dict | None = Field(default=None, alias="metadata_")


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
    def _tag_names(cls, value):
        if value is None:
            return []
        return [getattr(tag, "name", tag) for tag in value]

    model_config = {"from_attributes": True, "populate_by_name": True}


class SongVersionOut(BaseModel):
    id: UUID
    song_id: UUID
    version: int
    title: str
    artist: str
    capo: int
    key: str | None
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SongWithVersions(BaseModel):
    song: SongOut
    versions: list[SongVersionOut]
