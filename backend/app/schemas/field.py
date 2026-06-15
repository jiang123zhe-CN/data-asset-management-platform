from datetime import datetime
from pydantic import BaseModel, Field as PydField


class FieldCreate(BaseModel):
    field_code: str = PydField(min_length=1, max_length=100)
    name: str = PydField(min_length=1, max_length=200)
    english_name: str | None = None
    data_type: str = PydField(min_length=1, max_length=50)
    length: int | None = None
    precision: int | None = None
    table_name: str = PydField(min_length=1, max_length=200)
    database_name: str | None = None
    business_domain: str | None = None
    sensitivity_level: str = "L2"
    description: str | None = None
    business_rules: str | None = None
    finance_category_id: int | None = None  # 金融合规67类分类
    finance_data_level: str | None = None   # core/important/sensitive/normal


class FieldUpdate(BaseModel):
    field_code: str | None = None
    name: str | None = None
    english_name: str | None = None
    data_type: str | None = None
    length: int | None = None
    precision: int | None = None
    table_name: str | None = None
    database_name: str | None = None
    business_domain: str | None = None
    sensitivity_level: str | None = None
    description: str | None = None
    business_rules: str | None = None
    status: str | None = None
    finance_category_id: int | None = None
    finance_data_level: str | None = None


class FieldResponse(BaseModel):
    id: int
    field_code: str
    name: str
    english_name: str | None = None
    data_type: str
    length: int | None = None
    precision: int | None = None
    table_name: str
    database_name: str | None = None
    business_domain: str | None = None
    sensitivity_level: str
    description: str | None = None
    business_rules: str | None = None
    status: str
    is_anomaly: bool
    anomaly_type: str | None = None
    source: str
    finance_category_id: int | None = None
    finance_category_name: str | None = None
    finance_category_path: str | None = None
    finance_data_level: str | None = None
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ImportRecordResponse(BaseModel):
    id: int
    file_name: str
    file_size: int | None = None
    total_rows: int
    success_rows: int
    failed_rows: int
    status: str
    error_details: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
