from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey

from app.core.database import Base


class Directory(Base):
    __tablename__ = "directories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    code = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    tags = Column(String(500), nullable=True)
    parent_id = Column(Integer, ForeignKey("directories.id"), nullable=True, index=True)
    level = Column(Integer, nullable=False, default=0)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
