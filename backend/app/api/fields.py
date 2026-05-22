import io
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
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
    if sensitivity_level:
        query = query.filter(Field.sensitivity_level == sensitivity_level)
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

    return PaginatedResponse(
        items=[FieldResponse.model_validate(f) for f in items],
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
):
    if db.query(Field).filter(Field.field_code == body.field_code).first():
        raise HTTPException(status_code=400, detail="Field code already exists")
    field = Field(**body.model_dump(), created_by=current_user.id)
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


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
    return field


@router.delete("/{field_id}")
def delete_field(
    field_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("data_admin", "admin")),
):
    field = db.query(Field).filter(Field.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    field.status = "inactive"
    db.commit()
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
):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .xlsx/.xls files are supported")
    content = file.file.read()
    result = import_fields(db, io.BytesIO(content), current_user, file.filename, len(content))
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
