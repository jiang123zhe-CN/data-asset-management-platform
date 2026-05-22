from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey

from app.core.database import Base


class ReviewRecord(Base):
    __tablename__ = "review_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_status = Column(String(20), nullable=False, default="pending", index=True)
    review_type = Column(String(20), nullable=False, default="anomaly")
    anomaly_type = Column(String(50), nullable=True)
    original_data = Column(Text, nullable=True)
    modified_data = Column(Text, nullable=True)
    comment = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
