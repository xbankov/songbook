import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Song(Base):
    __tablename__ = "songs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(512), nullable=False, index=True)
    artist = Column(String(512), nullable=False, index=True, default="Unknown")
    capo = Column(Integer, nullable=False, default=0)
    key = Column(String(16), nullable=True)
    body = Column(Text, nullable=False, default="")
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    versions = relationship(
        "SongVersion", back_populates="song", lazy="selectin", cascade="all, delete-orphan"
    )
    songbook_entries = relationship(
        "SongbookEntry", back_populates="song", lazy="selectin", cascade="all, delete-orphan"
    )


class SongVersion(Base):
    __tablename__ = "song_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    song_id = Column(UUID(as_uuid=True), ForeignKey("songs.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    title = Column(String(512), nullable=False)
    artist = Column(String(512), nullable=False)
    capo = Column(Integer, nullable=False, default=0)
    key = Column(String(16), nullable=True)
    body = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint("song_id", "version", name="uq_song_version"),
    )

    song = relationship("Song", back_populates="versions", lazy="selectin")
