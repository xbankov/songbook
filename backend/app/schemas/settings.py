from uuid import UUID

from pydantic import BaseModel, field_validator


class SettingsOut(BaseModel):
    id: UUID
    transpose: int
    double_column: bool
    font: str
    font_size: int
    display_mode: str

    model_config = {"from_attributes": True}

    @field_validator("double_column", mode="before")
    @classmethod
    def coerce_double_column(cls, v):
        if isinstance(v, int):
            return bool(v)
        return v


class SettingsUpdate(BaseModel):
    transpose: int | None = None
    double_column: bool | None = None
    font: str | None = None
    font_size: int | None = None
    display_mode: str | None = None

    @field_validator("double_column", mode="before")
    @classmethod
    def coerce_double_column(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, int):
            return bool(v)
        return v
