from datetime import datetime
from pydantic import BaseModel


class ReviewSubmit(BaseModel):
    status: str  # approved, corrected, rejected
    comment: str | None = None
    corrected_field_data: dict | None = None


class ReviewResponse(BaseModel):
    id: int
    field_id: int
    reviewer_id: int | None = None
    review_status: str
    review_type: str
    anomaly_type: str | None = None
    original_data: str | None = None
    modified_data: str | None = None
    comment: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewStatsResponse(BaseModel):
    pending: int = 0
    approved: int = 0
    corrected: int = 0
    rejected: int = 0
    total: int = 0
