import json
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.field import Field
from app.models.review_record import ReviewRecord
from app.services.anomaly_detector import detect_anomalies
from app.schemas.review import ReviewSubmit, ReviewResponse, ReviewStatsResponse
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/api/reviews", tags=["Reviews"])


@router.get("/", response_model=PaginatedResponse[dict])
def list_reviews(
    status: str | None = None,
    review_type: str | None = None,
    anomaly_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(ReviewRecord)
    if status:
        query = query.filter(ReviewRecord.review_status == status)
    if review_type:
        query = query.filter(ReviewRecord.review_type == review_type)
    if anomaly_type:
        query = query.filter(ReviewRecord.anomaly_type == anomaly_type)

    total = query.count()
    items = query.order_by(ReviewRecord.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for r in items:
        field = db.query(Field).filter(Field.id == r.field_id).first()
        result.append({
            "id": r.id,
            "field_id": r.field_id,
            "reviewer_id": r.reviewer_id,
            "review_status": r.review_status,
            "review_type": r.review_type,
            "anomaly_type": r.anomaly_type,
            "original_data": r.original_data,
            "modified_data": r.modified_data,
            "comment": r.comment,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            "created_at": r.created_at.isoformat(),
            "field_code": field.field_code if field else None,
            "field_name": field.name if field else None,
            "field_table": field.table_name if field else None,
        })

    return PaginatedResponse(
        items=result,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/stats", response_model=ReviewStatsResponse)
def get_review_stats(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    all_reviews = db.query(ReviewRecord)
    return ReviewStatsResponse(
        pending=all_reviews.filter(ReviewRecord.review_status == "pending").count(),
        approved=all_reviews.filter(ReviewRecord.review_status == "approved").count(),
        corrected=all_reviews.filter(ReviewRecord.review_status == "corrected").count(),
        rejected=all_reviews.filter(ReviewRecord.review_status == "rejected").count(),
        total=all_reviews.count(),
    )


@router.get("/{review_id}")
def get_review(review_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    r = db.query(ReviewRecord).filter(ReviewRecord.id == review_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")
    field = db.query(Field).filter(Field.id == r.field_id).first()
    return {
        "id": r.id,
        "field_id": r.field_id,
        "review_status": r.review_status,
        "review_type": r.review_type,
        "anomaly_type": r.anomaly_type,
        "original_data": r.original_data,
        "modified_data": r.modified_data,
        "comment": r.comment,
        "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
        "created_at": r.created_at.isoformat(),
        "current_field": {
            "field_code": field.field_code,
            "name": field.name,
            "english_name": field.english_name,
            "data_type": field.data_type,
            "table_name": field.table_name,
            "database_name": field.database_name,
            "business_domain": field.business_domain,
            "sensitivity_level": field.sensitivity_level,
            "description": field.description,
        } if field else None,
    }


@router.put("/{review_id}")
def submit_review(
    review_id: int,
    body: ReviewSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("reviewer", "admin")),
):
    r = db.query(ReviewRecord).filter(ReviewRecord.id == review_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")
    if r.review_status != "pending":
        raise HTTPException(status_code=400, detail="Review is already processed")

    r.reviewer_id = current_user.id
    r.review_status = body.status
    r.comment = body.comment
    r.reviewed_at = datetime.now(timezone.utc)

    if body.corrected_field_data:
        r.modified_data = json.dumps(body.corrected_field_data, ensure_ascii=False)
        field = db.query(Field).filter(Field.id == r.field_id).first()
        if field:
            for key, val in body.corrected_field_data.items():
                if hasattr(field, key):
                    setattr(field, key, val)
            field.is_anomaly = False
            field.anomaly_type = None

    r.modified_data = json.dumps(body.dict(), ensure_ascii=False)
    db.commit()
    return {"message": "Review submitted"}


@router.post("/auto-detect")
def trigger_anomaly_detection(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("reviewer", "admin")),
):
    created = detect_anomalies(db)
    return {"created": len(created), "message": f"Detected {len(created)} anomalies"}


@router.get("/history/list")
def review_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("reviewer", "admin")),
):
    query = db.query(ReviewRecord).filter(ReviewRecord.review_status != "pending").order_by(ReviewRecord.reviewed_at.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[ReviewResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )
