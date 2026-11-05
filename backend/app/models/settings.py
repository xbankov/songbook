import uuid

from app.database import Base
from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import UUID


class Settings(Base):
    __tablename__ = "settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transpose = Column(Integer, nullable=False, default=0)
    double_column = Column(Integer, nullable=False, default=0)
    font = Column(String(128), nullable=False, default="DejaVu Sans Mono")
    font_size = Column(Integer, nullable=False, default=9)
    display_mode = Column(String(16), nullable=False, default="above")
