import json

from sqlalchemy.orm import Session

from app.models.field import Field
from app.models.mapping import DirectoryFieldMapping
from app.models.review_record import ReviewRecord


def detect_anomalies(db: Session) -> list[ReviewRecord]:
    """Scan fields for anomalies and create review records."""
    created = []

    # 1. Unmapped fields
    mapped_ids = {m.field_id for m in db.query(DirectoryFieldMapping).all()}
    unmapped = db.query(Field).filter(
        Field.id.notin_(mapped_ids),
        Field.status == "active",
        Field.is_anomaly == False,
    ).all()

    for f in unmapped:
        if not _has_pending_review(db, f.id, "unmapped"):
            f.is_anomaly = True
            f.anomaly_type = "unmapped"
            r = ReviewRecord(
                field_id=f.id,
                review_status="pending",
                review_type="anomaly",
                anomaly_type="unmapped",
                original_data=json.dumps({
                    "field_code": f.field_code,
                    "name": f.name,
                    "table_name": f.table_name,
                    "data_type": f.data_type,
                }, ensure_ascii=False),
            )
            db.add(r)
            created.append(r)

    # 2. Missing required info
    incomplete = db.query(Field).filter(
        (Field.data_type == None) | (Field.table_name == None) | (Field.name == None),
        Field.status == "active",
        Field.is_anomaly == False,
    ).all()

    for f in incomplete:
        if not _has_pending_review(db, f.id, "missing_info"):
            f.is_anomaly = True
            f.anomaly_type = "missing_info"
            r = ReviewRecord(
                field_id=f.id,
                review_status="pending",
                review_type="anomaly",
                anomaly_type="missing_info",
                original_data=json.dumps({
                    "field_code": f.field_code,
                    "name": f.name,
                    "data_type": f.data_type,
                    "table_name": f.table_name,
                }, ensure_ascii=False),
            )
            db.add(r)
            created.append(r)

    db.commit()
    return created


def _has_pending_review(db: Session, field_id: int, anomaly_type: str) -> bool:
    return db.query(ReviewRecord).filter(
        ReviewRecord.field_id == field_id,
        ReviewRecord.review_status == "pending",
        ReviewRecord.review_type == "anomaly",
        ReviewRecord.anomaly_type == anomaly_type,
    ).first() is not None
