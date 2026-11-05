import uuid
from datetime import datetime, timezone

from app.database import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class Songbook(Base):
    __tablename__ = "songbooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(512), nullable=False)
    description = Column(Text, nullable=True, default="")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    entries = relationship(
        "SongbookEntry",
        back_populates="songbook",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class SongbookEntry(Base):
    __tablename__ = "songbook_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    songbook_id = Column(
        UUID(as_uuid=True),
        ForeignKey("songbooks.id", ondelete="CASCADE"),
        nullable=False,
    )
    song_id = Column(
        UUID(as_uuid=True), ForeignKey("songs.id", ondelete="CASCADE"), nullable=False
    )
    sort_order = Column(Integer, nullable=False, default=0)
    transpose = Column(Integer, nullable=False, default=0)
    double_column = Column(Integer, nullable=False, default=0)

    songbook = relationship("Songbook", back_populates="entries", lazy="selectin")
    song = relationship("Song", lazy="selectin")
