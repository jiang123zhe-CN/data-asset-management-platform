from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.field import Field
from app.models.directory import Directory
from app.models.mapping import DirectoryFieldMapping
from app.models.review_record import ReviewRecord
from app.services.excel_service import export_fields_to_excel

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/summary")
def get_summary(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    total_fields = db.query(Field).filter(Field.status == "active").count()
    total_dirs = db.query(Directory).filter(Directory.is_active == True).count()
    total_mappings = db.query(DirectoryFieldMapping).count()
    pending_reviews = db.query(ReviewRecord).filter(ReviewRecord.review_status == "pending").count()
    anomaly_count = db.query(Field).filter(Field.is_anomaly == True).count()

    return {
        "total_fields": total_fields,
        "total_directories": total_dirs,
        "total_mappings": total_mappings,
        "pending_reviews": pending_reviews,
        "anomaly_count": anomaly_count,
    }


@router.get("/by-directory")
def get_by_directory(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    dirs = db.query(Directory).filter(Directory.is_active == True).all()
    result = []
    for d in dirs:
        count = db.query(DirectoryFieldMapping).filter(DirectoryFieldMapping.directory_id == d.id).count()
        result.append({"directory_id": d.id, "name": d.name, "code": d.code, "field_count": count})
    return result


@router.get("/by-sensitivity")
def get_by_sensitivity(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    from sqlalchemy import func
    result = db.query(Field.sensitivity_level, func.count(Field.id)).filter(Field.status == "active").group_by(Field.sensitivity_level).all()
    return [{"sensitivity_level": r[0], "count": r[1]} for r in result]


@router.get("/export/fields")
def export_fields_report(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    fields = db.query(Field).all()
    output = export_fields_to_excel(fields)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=data_fields_report.xlsx"},
    )


@router.get("/export/mappings")
def export_mappings_report(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    import io
    import openpyxl

    mappings = db.query(DirectoryFieldMapping).all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "映射关系"
    ws.append(["映射ID", "字段ID", "字段编码", "字段名称", "目录ID", "目录名称", "映射来源", "置信度", "创建时间"])

    for m in mappings:
        field = db.query(Field).filter(Field.id == m.field_id).first()
        directory = db.query(Directory).filter(Directory.id == m.directory_id).first()
        ws.append([
            m.id, m.field_id,
            field.field_code if field else "", field.name if field else "",
            m.directory_id, directory.name if directory else "",
            m.mapping_source, m.confidence,
            m.created_at.isoformat() if m.created_at else "",
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=mappings_report.xlsx"},
    )
