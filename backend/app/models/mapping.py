from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint

from app.core.database import Base


class DirectoryFieldMapping(Base):
    __tablename__ = "directory_field_mappings"
    __table_args__ = (UniqueConstraint("directory_id", "field_id", name="uq_directory_field"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    directory_id = Column(Integer, ForeignKey("directories.id"), nullable=False, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    mapping_type = Column(String(20), default="direct")
    mapping_source = Column(String(20), default="manual")
    confidence = Column(Float, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
