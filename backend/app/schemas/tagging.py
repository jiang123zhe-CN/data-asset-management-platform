from datetime import datetime
from pydantic import BaseModel, Field


class TaggingRunRequest(BaseModel):
    field_ids: list[int] | None = None
    mode: str = "full"  # "rules_only" | "ai_only" | "full"


class TaggingRunStatus(BaseModel):
    task_id: str
    status: str
    processed: int = 0
    classified: int = 0
    tiered: int = 0
    errors: list[dict] = []


class TaggingFieldResponse(BaseModel):
    id: int
    field_code: str
    name: str
    data_type: str
    table_name: str
    business_domain: str | None = None
    sensitivity_level: str
    classification_id: int | None = None
    classification_name: str | None = None
    finance_category_id: int | None = None
    finance_category_name: str | None = None
    finance_category_path: str | None = None  # "业务数据 > 金融市场数据 > 股票数据"
    finance_data_level: str | None = None
    tagging_method: str | None = None
    tagging_confidence: float | None = None
    last_tagged_at: datetime | None = None
    is_anomaly: bool = False

    model_config = {"from_attributes": True}


class TaggingBatchUpdate(BaseModel):
    field_ids: list[int]
    finance_category_id: int | None = None
    finance_data_level: str | None = None
    confidence: float = 1.0
    comment: str = ""


class TaggingManualUpdate(BaseModel):
    finance_category_id: int | None = None
    finance_data_level: str | None = None
    confidence: float = 1.0
    comment: str = ""


class TaggingHistoryResponse(BaseModel):
    id: int
    field_id: int
    action: str
    old_category_id: int | None = None
    new_category_id: int | None = None
    old_tier_level: str | None = None
    new_tier_level: str | None = None
    old_confidence: float | None = None
    new_confidence: float | None = None
    tagging_method: str | None = None
    operator_id: int | None = None
    comment: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaggingStats(BaseModel):
    total_fields: int
    classified_count: int
    unclassified_count: int
    coverage_pct: float
    by_tier: dict
    by_method: dict
    by_category: dict
