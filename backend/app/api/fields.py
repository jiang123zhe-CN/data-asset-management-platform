import io
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.field import Field, ImportRecord
from app.schemas.field import FieldCreate, FieldUpdate, FieldResponse, ImportRecordResponse
from app.schemas.common import PaginatedResponse
from app.services.excel_service import generate_template, import_fields, export_fields_to_excel
from app.services.log_service import log_action

router = APIRouter(prefix="/api/fields", tags=["Fields"])


@router.get("/", response_model=PaginatedResponse[FieldResponse])
def list_fields(
    search: str | None = None,
    field_code: str | None = None,
    name: str | None = None,
    data_type: str | None = None,
    table_name: str | None = None,
    business_domain: str | None = None,
    sensitivity_level: str | None = None,
    finance_data_level: str | None = None,
    is_anomaly: bool | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Field)

    if search:
        like = f"%{search}%"
        query = query.filter(
            (Field.field_code.ilike(like))
            | (Field.name.ilike(like))
            | (Field.table_name.ilike(like))
            | (Field.english_name.ilike(like))
        )
    if field_code:
        query = query.filter(Field.field_code.ilike(f"%{field_code}%"))
    if name:
        query = query.filter(Field.name.ilike(f"%{name}%"))
    if data_type:
        query = query.filter(Field.data_type == data_type)
    if table_name:
        query = query.filter(Field.table_name.ilike(f"%{table_name}%"))
    if business_domain:
        query = query.filter(Field.business_domain == business_domain)
    if finance_data_level:
        query = query.filter(Field.finance_data_level == finance_data_level)
    if sensitivity_level:
        query = query.filter(Field.sensitivity_level == sensitivity_level)  # deprecated
    if is_anomaly is not None:
        query = query.filter(Field.is_anomaly == is_anomaly)
    if status:
        query = query.filter(Field.status == status)

    total = query.count()
    sort_col = getattr(Field, sort_by, Field.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    items = query.offset((page - 1) * page_size).limit(page_size).all()

    # Populate finance_category_name + path from finance_data_categories
    from app.models.finance_category import FinanceDataCategory
    fin_cat_ids = [f.finance_category_id for f in items if f.finance_category_id]
    fin_cat_map: dict[int, str] = {}
    fin_path_map: dict[int, str] = {}
    if fin_cat_ids:
        fin_cats = db.query(FinanceDataCategory).filter(FinanceDataCategory.id.in_(fin_cat_ids)).all()
        fin_cat_map = {c.id: c.name for c in fin_cats}
        all_fin = db.query(FinanceDataCategory).filter(FinanceDataCategory.is_active == True).all()
        id_to_cat = {c.id: c for c in all_fin}
        for c in fin_cats:
            parts = [c.name]
            pid = c.parent_id
            while pid and pid in id_to_cat:
                parts.append(id_to_cat[pid].name)
                pid = id_to_cat[pid].parent_id
            fin_path_map[c.id] = " > ".join(reversed(parts))

    result_items = []
    for f in items:
        d = FieldResponse.model_validate(f)
        d.finance_category_name = fin_cat_map.get(f.finance_category_id)
        d.finance_category_path = fin_path_map.get(f.finance_category_id)
        result_items.append(d)

    return PaginatedResponse(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.post("/", response_model=FieldResponse, status_code=201)
def create_field(
    body: FieldCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("data_entry", "data_admin", "admin")),
    request: Request = None,
):
    if db.query(Field).filter(Field.field_code == body.field_code).first():
        raise HTTPException(status_code=400, detail="Field code already exists")
    field = Field(**body.model_dump(), created_by=current_user.id)
    db.add(field)
    db.commit()
    db.refresh(field)

    # Auto-classify via compliance engine (国信办通字〔2026〕2号)
    from app.services.compliance_engine import ComplianceEngine
    comp = ComplianceEngine(db)
    comp.classify_fields([field.id])
    db.refresh(field)
    db.commit()

    log_action(db, user_id=current_user.id, username=current_user.username,
               action="create", module="fields", target_type="field", target_id=field.id,
               detail={"field_code": field.field_code, "name": field.name},
               ip_address=request.client.host if request else None)

    # Populate category name for response
    resp = FieldResponse.model_validate(field)
    if field.finance_category_id:
        from app.models.finance_category import FinanceDataCategory
        cat = db.query(FinanceDataCategory).filter(FinanceDataCategory.id == field.finance_category_id).first()
        resp.finance_category_name = cat.name if cat else None
    return resp


@router.get("/{field_id}", response_model=FieldResponse)
def get_field(field_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    field = db.query(Field).filter(Field.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    return field


@router.put("/{field_id}", response_model=FieldResponse)
def update_field(
    field_id: int,
    body: FieldUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("data_entry", "data_admin", "reviewer", "admin")),
    request: Request = None,
):
    field = db.query(Field).filter(Field.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    update_data = body.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(field, key, val)
    field.updated_by = current_user.id
    field.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(field)
    log_action(db, user_id=current_user.id, username=current_user.username,
               action="update", module="fields", target_type="field", target_id=field.id,
               detail={"changed": list(update_data.keys())},
               ip_address=request.client.host if request else None)
    return field


@router.delete("/{field_id}")
def delete_field(
    field_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("data_admin", "admin")),
    request: Request = None,
):
    field = db.query(Field).filter(Field.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    field.status = "inactive"
    db.commit()
    log_action(db, user_id=current_user.id, username=current_user.username,
               action="delete", module="fields", target_type="field", target_id=field_id,
               detail={"field_code": field.field_code},
               ip_address=request.client.host if request else None)
    return {"message": "Field deactivated"}


@router.get("/import/template")
def download_template():
    output = generate_template()
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=field_import_template.xlsx"},
    )


@router.post("/import", response_model=ImportRecordResponse)
def import_fields_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("data_entry", "data_admin", "admin")),
    request: Request = None,
):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .xlsx/.xls files are supported")
    content = file.file.read()
    result = import_fields(db, io.BytesIO(content), current_user, file.filename, len(content))
    log_action(db, user_id=current_user.id, username=current_user.username,
               action="import", module="fields", target_type="import_record", target_id=result.id,
               detail={"file_name": file.filename, "total": result.total_rows, "success": result.success_rows},
               ip_address=request.client.host if request else None)
    return result


@router.get("/import/history", response_model=list[ImportRecordResponse])
def import_history(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return db.query(ImportRecord).order_by(ImportRecord.created_at.desc()).limit(50).all()


@router.get("/import/{import_id}/errors")
def import_errors(
    import_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    record = db.query(ImportRecord).filter(ImportRecord.id == import_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Import record not found")
    if not record.error_details:
        return {"errors": []}
    import json
    return {"errors": json.loads(record.error_details)}


@router.get("/export/excel")
def export_fields(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    fields = db.query(Field).all()
    output = export_fields_to_excel(fields)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=data_fields.xlsx"},
    )
