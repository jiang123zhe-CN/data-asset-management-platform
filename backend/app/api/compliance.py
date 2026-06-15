"""金融合规分类分级 API — Finance Data Categories + Compliance Engine"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.finance_category import FinanceDataCategory, FinanceGradingRule
from app.schemas.standard import (
    FinanceCategoryCreate, FinanceCategoryUpdate, FinanceCategoryResponse,
    FinanceCategoryTreeNode, FinanceGradingRuleResponse,
    ComplianceClassifyRequest, ComplianceClassifyResult,
)
from app.services.compliance_engine import ComplianceEngine

router = APIRouter(prefix="/api/compliance", tags=["Compliance"])


# ═══════════════════════════════════════════════════════════════════════════
# Finance Categories (67类三级标准分类)
# ═══════════════════════════════════════════════════════════════════════════

def _build_tree_node(cat: FinanceDataCategory, db: Session) -> FinanceCategoryTreeNode:
    children_count = (
        db.query(FinanceDataCategory)
        .filter(
            FinanceDataCategory.parent_id == cat.id,
            FinanceDataCategory.is_active == True,
        )
        .count()
    )
    return FinanceCategoryTreeNode(
        id=cat.id,
        name=cat.name,
        code=cat.code,
        parent_id=cat.parent_id,
        level=cat.level,
        data_type=cat.data_type,
        finance_product=cat.finance_product,
        ref_min_level=cat.ref_min_level,
        children_count=children_count,
    )


@router.get("/categories/tree/", response_model=list[FinanceCategoryTreeNode])
@router.get("/categories/tree", response_model=list[FinanceCategoryTreeNode])
def get_finance_category_tree(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """返回三层树结构：一级(3) → 二级(9) → 三级(67)。"""
    cats = (
        db.query(FinanceDataCategory)
        .filter(FinanceDataCategory.is_active == True)
        .order_by(FinanceDataCategory.level, FinanceDataCategory.sort_order)
        .all()
    )
    return [_build_tree_node(c, db) for c in cats]


@router.get("/categories/", response_model=list[FinanceCategoryResponse])
def list_finance_categories(
    data_type: str | None = None,
    level: int | None = None,
    parent_id: int | None = None,
    finance_product: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """分条件查询金融合规分类。"""
    q = db.query(FinanceDataCategory).filter(FinanceDataCategory.is_active == True)
    if data_type:
        q = q.filter(FinanceDataCategory.data_type == data_type)
    if level is not None:
        q = q.filter(FinanceDataCategory.level == level)
    if parent_id is not None:
        q = q.filter(FinanceDataCategory.parent_id == parent_id)
    if finance_product:
        q = q.filter(FinanceDataCategory.finance_product == finance_product)
    return q.order_by(FinanceDataCategory.level, FinanceDataCategory.sort_order).all()


@router.get("/categories/{cat_id}", response_model=FinanceCategoryResponse)
def get_finance_category(cat_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    cat = db.query(FinanceDataCategory).filter(
        FinanceDataCategory.id == cat_id, FinanceDataCategory.is_active == True
    ).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return cat


@router.put("/categories/{cat_id}", response_model=FinanceCategoryResponse)
def update_finance_category(
    cat_id: int,
    body: FinanceCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("system_admin", "admin")),
):
    cat = db.query(FinanceDataCategory).filter(
        FinanceDataCategory.id == cat_id, FinanceDataCategory.is_active == True
    ).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    if body.code and body.code != cat.code:
        if db.query(FinanceDataCategory).filter(FinanceDataCategory.code == body.code).first():
            raise HTTPException(status_code=400, detail="Code already exists")
        cat.code = body.code

    updatable = ["name", "data_type", "finance_product", "ref_min_level",
                 "level_rationale", "appendix_desc", "appendix_example",
                 "mapped_category_id", "sort_order"]
    for field_name in updatable:
        val = getattr(body, field_name, None)
        if val is not None:
            setattr(cat, field_name, val)

    if body.is_active is not None:
        cat.is_active = body.is_active

    cat.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(cat)
    return cat


# ═══════════════════════════════════════════════════════════════════════════
# Compliance Classification (合规分类分级执行)
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/classify/", response_model=list[ComplianceClassifyResult])
@router.post("/classify", response_model=list[ComplianceClassifyResult])
def run_compliance_classify(
    body: ComplianceClassifyRequest | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("data_admin", "system_admin", "admin")),
):
    """执行金融合规分类分级（矩阵判定 + 就高从严）。

    对所有活跃字段（或指定 field_ids），按《金融信息服务数据分类分级指南》：
    ① 匹配 67 类三级标准分类
    ② 按影响对象×危害程度矩阵判定数据级别
    ③ 应用就高从严原则（表级继承）
    ④ 结果持久化到 field 的 finance_category_id + finance_data_level
    """
    engine = ComplianceEngine(db)
    results = engine.classify_fields(body.field_ids if body else None)
    return [ComplianceClassifyResult(**r) for r in results]


@router.get("/threshold/")
@router.get("/threshold")
def check_threshold(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """检测核心/重要数据的30%变化阈值。"""
    engine = ComplianceEngine(db)
    return engine.check_threshold()


@router.get("/table-level/")
@router.get("/table-level")
def get_table_level(
    table_name: str = Query(..., description="表名"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """获取指定表的最高金融数据级别（就高从严）。"""
    engine = ComplianceEngine(db)
    return engine.get_table_level(table_name)


# ═══════════════════════════════════════════════════════════════════════════
# Grading Rules (分级矩阵规则)
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/grading-rules/", response_model=list[FinanceGradingRuleResponse])
def list_grading_rules(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return (
        db.query(FinanceGradingRule)
        .filter(FinanceGradingRule.is_active == True)
        .order_by(FinanceGradingRule.priority.desc())
        .all()
    )


@router.get("/grading-rules/matrix/")
@router.get("/grading-rules/matrix")
def get_grading_matrix(_: User = Depends(get_current_user)):
    """返回完整的分级判定矩阵。"""
    from app.services.compliance_engine import GRADING_MATRIX
    return {
        "description": "影响对象 × 危害程度 → 数据级别",
        "impact_targets": [
            "national_security", "economy", "social_order",
            "public_interest", "org_rights", "personal_rights",
        ],
        "impact_levels": ["extremely_serious", "serious", "general"],
        "data_levels": ["core", "important", "sensitive", "normal"],
        "matrix": {f"{t}/{l}": v for (t, l), v in sorted(GRADING_MATRIX.items())},
    }
