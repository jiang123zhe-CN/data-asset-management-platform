from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey

from app.core.database import Base


class Field(Base):
    __tablename__ = "fields"

    id = Column(Integer, primary_key=True, autoincrement=True)
    field_code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    english_name = Column(String(200), nullable=True)
    data_type = Column(String(50), nullable=False)
    length = Column(Integer, nullable=True)
    precision = Column(Integer, nullable=True)
    table_name = Column(String(200), nullable=False)
    database_name = Column(String(200), nullable=True)
    business_domain = Column(String(100), nullable=True, index=True)
    sensitivity_level = Column(String(20), nullable=False, default="L1", index=True)
    description = Column(Text, nullable=True)
    business_rules = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="active")
    is_anomaly = Column(Boolean, nullable=False, default=False)
    anomaly_type = Column(String(50), nullable=True)
    source = Column(String(20), nullable=False, default="manual")
    import_batch_id = Column(Integer, ForeignKey("import_records.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class ImportRecord(Base):
    __tablename__ = "import_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=True)
    total_rows = Column(Integer, nullable=False)
    success_rows = Column(Integer, nullable=False, default=0)
    failed_rows = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="processing")
    error_details = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
