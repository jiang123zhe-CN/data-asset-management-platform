import io
import math
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.field import Field
from app.models.directory import Directory
from app.models.mapping import DirectoryFieldMapping
from app.models.review_record import ReviewRecord
from app.schemas.mapping import (
    MappingCreate,
    MappingBatchCreate,
    MappingBatchDelete,
    MappingResponse,
    MappingDetailResponse,
    VisualizationData,
    VisualizationNode,
    VisualizationEdge,
    AutoMapTaskResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.llm_service import auto_map_fields
from app.services.excel_service import export_mappings_to_excel

router = APIRouter(prefix="/api/mappings", tags=["Mappings"])

# Simple in-memory task store for auto-map progress
_tasks: dict = {}


def _build_detail(m: DirectoryFieldMapping, db: Session) -> dict:
    field = db.query(Field).filter(Field.id == m.field_id).first()
    directory = db.query(Directory).filter(Directory.id == m.directory_id).first()
    path = _get_directory_path(m.directory_id, db)

    return {
        "id": m.id,
        "directory_id": m.directory_id,
        "directory_name": directory.name if directory else None,
        "directory_code": directory.code if directory else None,
        "directory_path": path,
        "field_id": m.field_id,
        "field_code": field.field_code if field else None,
        "field_name": field.name if field else None,
        "field_data_type": field.data_type if field else None,
        "field_table": field.table_name if field else None,
        "mapping_type": m.mapping_type,
        "mapping_source": m.mapping_source,
        "confidence": m.confidence,
        "created_at": m.created_at,
    }


def _get_directory_path(dir_id: int, db: Session) -> str:
    parts = []
    current = db.query(Directory).filter(Directory.id == dir_id).first()
    while current:
        parts.insert(0, current.name)
        current = db.query(Directory).filter(Directory.id == current.parent_id).first() if current.parent_id else None
    return " / ".join(parts)


@router.get("/", response_model=PaginatedResponse[MappingDetailResponse])
def list_mappings(
    directory_id: int | None = None,
    field_id: int | None = None,
    business_domain: str | None = None,
    mapping_source: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(DirectoryFieldMapping)

    if directory_id:
        query = query.filter(DirectoryFieldMapping.directory_id == directory_id)
    if field_id:
        query = query.filter(DirectoryFieldMapping.field_id == field_id)
    if mapping_source:
        query = query.filter(DirectoryFieldMapping.mapping_source == mapping_source)
    if business_domain:
        query = query.join(Field, DirectoryFieldMapping.field_id == Field.id).filter(
            Field.business_domain == business_domain
        )

    total = query.count()
    items = query.order_by(DirectoryFieldMapping.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[MappingDetailResponse(**_build_detail(m, db)) for m in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.post("/", response_model=MappingResponse, status_code=201)
def create_mapping(
    body: MappingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("data_admin", "admin")),
):
    existing = db.query(DirectoryFieldMapping).filter(
        DirectoryFieldMapping.directory_id == body.directory_id,
        DirectoryFieldMapping.field_id == body.field_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Mapping already exists")

    m = DirectoryFieldMapping(
        directory_id=body.directory_id,
        field_id=body.field_id,
        mapping_type=body.mapping_type,
        mapping_source="manual",
        created_by=current_user.id,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.post("/batch")
def batch_create_mappings(
    body: MappingBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("data_admin", "admin")),
):
    created = 0
    for fid in body.field_ids:
        existing = db.query(DirectoryFieldMapping).filter(
            DirectoryFieldMapping.directory_id == body.directory_id,
            DirectoryFieldMapping.field_id == fid,
        ).first()
        if not existing:
            db.add(DirectoryFieldMapping(
                directory_id=body.directory_id,
                field_id=fid,
                mapping_source="manual",
                created_by=current_user.id,
            ))
            created += 1
    db.commit()
    return {"created": created, "message": f"Created {created} mappings"}


@router.delete("/{mapping_id}")
def delete_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("data_admin", "admin")),
):
    m = db.query(DirectoryFieldMapping).filter(DirectoryFieldMapping.id == mapping_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Mapping not found")
    db.delete(m)
    db.commit()
    return {"message": "Mapping deleted"}


@router.post("/batch-delete")
def batch_delete_mappings(
    body: MappingBatchDelete,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("data_admin", "admin")),
):
    db.query(DirectoryFieldMapping).filter(DirectoryFieldMapping.id.in_(body.mapping_ids)).delete(synchronize_session=False)
    db.commit()
    return {"message": f"Deleted {len(body.mapping_ids)} mappings"}


@router.get("/visualization", response_model=VisualizationData)
def get_visualization_data(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    dirs = db.query(Directory).filter(Directory.is_active == True).all()
    fields = db.query(Field).all()
    mappings = db.query(DirectoryFieldMapping).all()

    dir_ids = {f"dir_{d.id}" for d in dirs}
    field_ids = {f"field_{f.id}" for f in fields}

    nodes = []
    for d in dirs:
        path = _get_directory_path(d.id, db)
        nodes.append(VisualizationNode(id=f"dir_{d.id}", label=d.name, node_type="directory", group=f"Level {d.level}"))
    for f in fields:
        nodes.append(VisualizationNode(
            id=f"field_{f.id}", label=f.name, node_type="field", group=f.sensitivity_level
        ))

    edges = []
    for m in mappings:
        edges.append(VisualizationEdge(source=f"field_{m.field_id}", target=f"dir_{m.directory_id}"))

    return VisualizationData(nodes=nodes, edges=edges)


@router.get("/unmapped-fields")
def get_unmapped_fields(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    mapped_ids = {m.field_id for m in db.query(DirectoryFieldMapping).all()}
    unmapped = db.query(Field).filter(Field.id.notin_(mapped_ids), Field.status == "active").all()
    return [{"id": f.id, "field_code": f.field_code, "name": f.name, "table_name": f.table_name} for f in unmapped]


@router.get("/stats")
def get_mapping_stats(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    total_fields = db.query(Field).filter(Field.status == "active").count()
    total_mappings = db.query(DirectoryFieldMapping).count()
    mapped_field_ids = {m.field_id for m in db.query(DirectoryFieldMapping).all()}
    unmapped = total_fields - len(mapped_field_ids)
    ai_mapped = db.query(DirectoryFieldMapping).filter(DirectoryFieldMapping.mapping_source == "ai_suggested").count()

    return {
        "total_fields": total_fields,
        "total_mappings": total_mappings,
        "unmapped_fields": unmapped,
        "ai_suggested_mappings": ai_mapped,
    }


@router.post("/auto-map", response_model=AutoMapTaskResponse)
def trigger_auto_map(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("data_admin", "admin")),
):
    task_id = str(uuid.uuid4())[:8]
    _tasks[task_id] = {"status": "running", "message": "AI auto-mapping started", "results": []}

    def _run():
        try:
            new_db = next(get_db())
            mapped_ids = {m.field_id for m in new_db.query(DirectoryFieldMapping).all()}
            unmapped = new_db.query(Field).filter(Field.id.notin_(mapped_ids), Field.status == "active").all()
            dirs = new_db.query(Directory).filter(Directory.is_active == True).all()

            if not unmapped:
                _tasks[task_id] = {"status": "completed", "total_fields": 0, "mapped_count": 0, "results": []}
                return

            # Exclude fields that already have pending AI mapping reviews
            pending_review_ids = {
                r.field_id for r in new_db.query(ReviewRecord).filter(
                    ReviewRecord.review_type == "ai_mapping",
                    ReviewRecord.review_status == "pending",
                ).all()
            }
            unmapped = [f for f in unmapped if f.id not in pending_review_ids]

            if not unmapped:
                _tasks[task_id] = {"status": "completed", "total_fields": 0, "mapped_count": 0, "results": []}
                return

            fields_data = [{"id": f.id, "name": f.name, "data_type": f.data_type, "table_name": f.table_name, "business_domain": f.business_domain, "description": f.description} for f in unmapped[:50]]
            dirs_data = [{"id": d.id, "name": d.name, "code": d.code, "level": d.level, "description": d.description, "tags": d.tags} for d in dirs]

            suggestions = auto_map_fields(fields_data, dirs_data)

            created = 0
            for s in suggestions:
                fid = s.get("field_id")
                did = s.get("directory_id")
                conf = s.get("confidence", 0.5)
                reason = s.get("reason", "")

                if fid and did:
                    dir_obj = new_db.query(Directory).filter(Directory.id == did).first()
                    field_obj = new_db.query(Field).filter(Field.id == fid).first()
                    if not dir_obj or not field_obj:
                        continue

                    new_db.add(ReviewRecord(
                        field_id=fid,
                        review_type="ai_mapping",
                        review_status="pending",
                        original_data=json.dumps({
                            "suggested_directory_id": did,
                            "directory_name": dir_obj.name,
                            "directory_code": dir_obj.code,
                            "confidence": conf,
                            "reason": reason,
                        }, ensure_ascii=False),
                    ))
                    created += 1

            new_db.commit()

            _tasks[task_id] = {
                "status": "completed",
                "total_fields": len(unmapped),
                "mapped_count": created,
                "results": suggestions,
            }
        except Exception as e:
            _tasks[task_id] = {"status": "failed", "message": str(e), "results": []}

    import json
    background_tasks.add_task(_run)
    return AutoMapTaskResponse(task_id=task_id, status="running", message="AI auto-mapping started")


@router.get("/auto-map/status/{task_id}")
def get_auto_map_status(task_id: str):
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/ai-suggestions")
def get_ai_suggestions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(DirectoryFieldMapping).filter(
        DirectoryFieldMapping.mapping_source == "ai_suggested"
    ).order_by(DirectoryFieldMapping.confidence.desc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[MappingDetailResponse(**_build_detail(m, db)) for m in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/export")
def export_mappings(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    mappings = db.query(DirectoryFieldMapping).order_by(DirectoryFieldMapping.created_at.desc()).all()
    data = [_build_detail(m, db) for m in mappings]
    excel_bytes = export_mappings_to_excel(data)
    return StreamingResponse(
        io.BytesIO(excel_bytes.getvalue()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=mappings_export.xlsx"},
    )
