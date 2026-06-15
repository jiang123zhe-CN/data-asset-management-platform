from datetime import datetime
from pydantic import BaseModel, Field


# ── Classification Category ──

class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=100)
    parent_id: int | None = None
    category_type: str = "business"
    description: str | None = None
    keywords: str | None = None
    regulatory_ref: str | None = None
    version: str = "v1.0"
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    code: str | None = Field(default=None, min_length=1, max_length=100)
    parent_id: int | None = None
    category_type: str | None = None
    description: str | None = None
    keywords: str | None = None
    regulatory_ref: str | None = None
    sort_order: int | None = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    code: str
    parent_id: int | None = None
    level: int
    category_type: str
    description: str | None = None
    keywords: str | None = None
    regulatory_ref: str | None = None
    version: str
    sort_order: int
    is_active: bool
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CategoryTreeNode(BaseModel):
    id: int
    name: str
    code: str
    parent_id: int | None = None
    level: int
    category_type: str
    children_count: int = 0


# ── Tiering Rule ──

class TieringRuleCreate(BaseModel):
    tier_level: str = Field(min_length=2, max_length=10)
    tier_name: str = Field(min_length=1, max_length=50)
    rule_type: str = "keyword"
    rule_content: str
    priority: int = 0
    regulatory_basis: str | None = None
    version: str = "v1.0"


class TieringRuleUpdate(BaseModel):
    tier_level: str | None = Field(default=None, min_length=2, max_length=10)
    tier_name: str | None = Field(default=None, min_length=1, max_length=50)
    rule_type: str | None = None
    rule_content: str | None = None
    priority: int | None = None
    regulatory_basis: str | None = None
    is_active: bool | None = None


class TieringRuleResponse(BaseModel):
    id: int
    tier_level: str
    tier_name: str
    rule_type: str
    rule_content: str
    priority: int
    regulatory_basis: str | None = None
    version: str
    is_active: bool
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Finance Data Categories (国信办通字〔2026〕2号) ──

class FinanceCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=50)
    parent_id: int | None = None
    data_type: str = "business"
    finance_product: str | None = None
    ref_min_level: str = "normal"
    level_rationale: str | None = None
    appendix_desc: str | None = None
    appendix_example: str | None = None
    mapped_category_id: int | None = None
    sort_order: int = 0


class FinanceCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    code: str | None = Field(default=None, min_length=1, max_length=50)
    parent_id: int | None = None
    data_type: str | None = None
    finance_product: str | None = None
    ref_min_level: str | None = None
    level_rationale: str | None = None
    appendix_desc: str | None = None
    appendix_example: str | None = None
    mapped_category_id: int | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class FinanceCategoryResponse(BaseModel):
    id: int
    code: str
    name: str
    level: int
    parent_id: int | None = None
    data_type: str
    finance_product: str | None = None
    ref_min_level: str
    level_rationale: str | None = None
    appendix_desc: str | None = None
    appendix_example: str | None = None
    mapped_category_id: int | None = None
    standard_ref: str | None = None
    version: str
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FinanceCategoryTreeNode(BaseModel):
    id: int
    name: str
    code: str
    parent_id: int | None = None
    level: int
    data_type: str
    finance_product: str | None = None
    ref_min_level: str
    children_count: int = 0


class FinanceGradingRuleResponse(BaseModel):
    id: int
    impact_target: str
    impact_level: str
    data_level: str
    priority: int
    description: str | None = None
    examples: str | None = None
    standard_ref: str | None = None

    model_config = {"from_attributes": True}


class ComplianceClassifyRequest(BaseModel):
    field_ids: list[int] | None = None


class ComplianceClassifyResult(BaseModel):
    field_id: int
    field_name: str
    finance_category_code: str | None = None
    finance_category_name: str | None = None
    finance_data_level: str | None = None
    ref_min_level: str | None = None
    level_upgraded: bool = False
    upgrade_reason: str | None = None
    confidence: float = 0.0
    method: str = "rule_engine"
