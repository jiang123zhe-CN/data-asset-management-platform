import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.field import Field
from app.models.standard import ClassificationCategory, TieringRule
from app.models.finance_category import FinanceDataCategory
from app.models.tagging import TaggingHistory
from app.schemas.tagging import (
    TaggingRunRequest, TaggingRunStatus, TaggingFieldResponse,
    TaggingBatchUpdate, TaggingManualUpdate, TaggingHistoryResponse, TaggingStats,
)
from app.services.tagging_service import TaggingPipeline

router = APIRouter(prefix="/api/tagging", tags=["Tagging"])

# In-memory task status storage (same pattern as mappings auto-map)
_tasks: dict[str, dict] = {}


@router.post("/run")
def run_tagging_pipeline(
    body: TaggingRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("data_admin", "admin")),
):
    task_id = str(uuid.uuid4())[:8]
    _tasks[task_id] = {"status": "running", "processed": 0, "classified": 0, "tiered": 0, "errors": []}

    pipeline = TaggingPipeline(db)

    def _run():
        try:
            result = pipeline.run(field_ids=body.field_ids, mode=body.mode)
            _tasks[task_id] = {"status": "completed", **result}
        except Exception as e:
            _tasks[task_id] = {"status": "failed", "processed": 0, "classified": 0, "tiered": 0,
                               "errors": [{"error": str(e)}]}

    background_tasks.add_task(_run)
    return {"task_id": task_id, "status": "running"}


@router.get("/run/{task_id}/status")
def get_task_status(task_id: str, _: User = Depends(get_current_user)):
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaggingRunStatus(task_id=task_id, **task)


@router.get("/results/")
def list_tagging_results(
    category_id: int | None = None,
    tier_level: str | None = None,
    finance_data_level: str | None = None,
    method: str | None = None,
    is_tagged: bool | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Field).filter(Field.status == "active")

    if category_id:
        q = q.filter(Field.finance_category_id == category_id)
    if tier_level:
        q = q.filter(Field.finance_data_level == tier_level)
    if finance_data_level:
        q = q.filter(Field.finance_data_level == finance_data_level)
    if method:
        q = q.filter(Field.tagging_method == method)
    if is_tagged is True:
        q = q.filter(Field.finance_category_id.isnot(None))
    elif is_tagged is False:
        q = q.filter(Field.finance_category_id.is_(None))
    if search:
        like = f"%{search}%"
        q = q.filter(
            Field.field_code.ilike(like) | Field.name.ilike(like) |
            Field.table_name.ilike(like) | Field.business_domain.ilike(like)
        )

    total = q.count()
    items = q.order_by(Field.tagging_confidence.desc().nullslast(), Field.updated_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    # Attach classification names (old + new)
    cat_map = {}
    cat_ids = [f.classification_id for f in items if f.classification_id]
    if cat_ids:
        cats = db.query(ClassificationCategory).filter(ClassificationCategory.id.in_(cat_ids)).all()
        cat_map = {c.id: c.name for c in cats}

    fin_cat_map: dict[int, str] = {}
    fin_path_map: dict[int, str] = {}
    fin_cat_ids = [f.finance_category_id for f in items if f.finance_category_id]
    if fin_cat_ids:
        fin_cats = db.query(FinanceDataCategory).filter(FinanceDataCategory.id.in_(fin_cat_ids)).all()
        fin_cat_map = {c.id: c.name for c in fin_cats}
        # Build 3-level path: "一级 > 二级 > 三级"
        all_fin = db.query(FinanceDataCategory).filter(FinanceDataCategory.is_active == True).all()
        id_to_cat = {c.id: c for c in all_fin}
        for c in fin_cats:
            parts = [c.name]
            pid = c.parent_id
            while pid and pid in id_to_cat:
                parts.append(id_to_cat[pid].name)
                pid = id_to_cat[pid].parent_id
            fin_path_map[c.id] = " > ".join(reversed(parts))

    result = []
    for f in items:
        result.append(TaggingFieldResponse(
            id=f.id, field_code=f.field_code, name=f.name,
            data_type=f.data_type, table_name=f.table_name,
            business_domain=f.business_domain, sensitivity_level=f.sensitivity_level,
            classification_id=f.classification_id,
            classification_name=cat_map.get(f.classification_id) if f.classification_id else None,
            finance_category_id=f.finance_category_id,
            finance_category_name=fin_cat_map.get(f.finance_category_id) if f.finance_category_id else None,
            finance_category_path=fin_path_map.get(f.finance_category_id) if f.finance_category_id else None,
            finance_data_level=f.finance_data_level,
            tagging_method=f.tagging_method, tagging_confidence=f.tagging_confidence,
            last_tagged_at=f.last_tagged_at, is_anomaly=f.is_anomaly,
        ))

    return {"items": [r.model_dump() for r in result], "total": total, "page": page, "page_size": page_size}


@router.put("/results/{field_id}")
def manual_update_tagging(
    field_id: int,
    body: TaggingManualUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("data_admin", "admin")),
):
    field = db.query(Field).filter(Field.id == field_id, Field.status == "active").first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    pipeline = TaggingPipeline(db)
    field = pipeline.manual_update(
        field=field,
        finance_category_id=body.finance_category_id,
        finance_data_level=body.finance_data_level,
        confidence=body.confidence,
        operator_id=current_user.id,
        comment=body.comment,
    )
    db.commit()
    return {"message": "Tagging updated"}


@router.put("/results/batch")
def batch_update_tagging(
    body: TaggingBatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("data_admin", "admin")),
):
    fields = db.query(Field).filter(Field.id.in_(body.field_ids), Field.status == "active").all()
    pipeline = TaggingPipeline(db)
    updated = 0
    for field in fields:
        pipeline.manual_update(
            field=field,
            finance_category_id=body.finance_category_id,
            finance_data_level=body.finance_data_level,
            confidence=body.confidence,
            operator_id=current_user.id,
            comment=body.comment,
        )
        updated += 1
    db.commit()
    return {"updated": updated}


@router.get("/results/{field_id}/history", response_model=list[TaggingHistoryResponse])
def get_tagging_history(field_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    field = db.query(Field).filter(Field.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    history = (
        db.query(TaggingHistory)
        .filter(TaggingHistory.field_id == field_id)
        .order_by(TaggingHistory.created_at.desc())
        .all()
    )
    return history


@router.get("/stats/", response_model=TaggingStats)
@router.get("/stats", response_model=TaggingStats)
def get_tagging_stats(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    total = db.query(Field).filter(Field.status == "active").count()
    classified = db.query(Field).filter(Field.status == "active", Field.finance_data_level.isnot(None)).count()
    unclassified = total - classified
    coverage = round(classified / total * 100, 1) if total else 0.0

    # By tier (finance_data_level)
    tiers = db.query(Field.finance_data_level, Field.id).filter(Field.status == "active").all()
    by_tier: dict[str, int] = {}
    for t, _ in tiers:
        key = t or "unclassified"
        by_tier[key] = by_tier.get(key, 0) + 1

    # By method
    methods = db.query(Field.tagging_method, Field.id).filter(Field.status == "active", Field.tagging_method.isnot(None)).all()
    by_method: dict[str, int] = {}
    for m, _ in methods:
        by_method[m] = by_method.get(m, 0) + 1

    # By category (finance_data_categories)
    cats = db.query(Field.finance_category_id).filter(Field.status == "active", Field.finance_category_id.isnot(None)).all()
    by_category: dict[str, int] = {}
    cat_map = {}
    cat_ids = [c[0] for c in cats if c[0]]
    if cat_ids:
        for c in db.query(FinanceDataCategory).filter(FinanceDataCategory.id.in_(cat_ids)).all():
            cat_map[c.id] = c.name
    for cid, in cats:
        if cid:
            name = cat_map.get(cid, str(cid))
            by_category[name] = by_category.get(name, 0) + 1

    return TaggingStats(
        total_fields=total, classified_count=classified, unclassified_count=unclassified,
        coverage_pct=coverage, by_tier=by_tier, by_method=by_method, by_category=by_category,
    )
