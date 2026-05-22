import io
import json
from typing import BinaryIO

import openpyxl
from sqlalchemy.orm import Session

from app.models.field import Field, ImportRecord
from app.models.user import User

TEMPLATE_HEADERS = [
    "field_code", "name", "english_name", "data_type", "length",
    "precision", "table_name", "database_name", "business_domain",
    "sensitivity_level", "description", "business_rules",
]

SENSITIVITY_OPTIONS = ["L1", "L2", "L3", "L4"]


def generate_template() -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "字段导入模板"
    ws.append(TEMPLATE_HEADERS)
    ws.append(["F001", "客户名称", "customer_name", "VARCHAR", 100, None, "dim_customer", "ods", "客户域", "L1", "客户姓名", ""])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def parse_excel(file: BinaryIO) -> list[dict]:
    wb = openpyxl.load_workbook(file, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    headers = [h.value for h in ws[1]]

    results = []
    for row_idx, row in enumerate(rows, start=2):
        if all(v is None for v in row):
            continue
        row_dict = {}
        for i, header in enumerate(TEMPLATE_HEADERS):
            val = row[i] if i < len(row) else None
            row_dict[header] = str(val).strip() if val is not None else None
        row_dict["_row"] = row_idx
        results.append(row_dict)

    wb.close()
    return results


def import_fields(db: Session, file: BinaryIO, user: User, file_name: str, file_size: int) -> ImportRecord:
    rows = parse_excel(file)
    total = len(rows)
    errors = []
    success = 0

    import_record = ImportRecord(
        user_id=user.id,
        file_name=file_name,
        file_size=file_size,
        total_rows=total,
        success_rows=0,
        failed_rows=0,
        status="processing",
    )
    db.add(import_record)
    db.flush()

    for row in rows:
        rownum = row.pop("_row")
        row_errors = []

        if not row.get("field_code"):
            row_errors.append({"row": rownum, "field": "field_code", "message": "字段编码不能为空"})
        if not row.get("name"):
            row_errors.append({"row": rownum, "field": "name", "message": "字段名称不能为空"})
        if not row.get("data_type"):
            row_errors.append({"row": rownum, "field": "data_type", "message": "数据类型不能为空"})
        if not row.get("table_name"):
            row_errors.append({"row": rownum, "field": "table_name", "message": "表名不能为空"})

        sl = row.get("sensitivity_level", "L1")
        if sl and sl not in SENSITIVITY_OPTIONS:
            row_errors.append({"row": rownum, "field": "sensitivity_level", "message": f"敏感等级必须为 {SENSITIVITY_OPTIONS}"})
            sl = "L1"

        existing = db.query(Field).filter(Field.field_code == row["field_code"]).first()
        if existing:
            row_errors.append({"row": rownum, "field": "field_code", "message": "字段编码已存在"})

        length_val = None
        if row.get("length"):
            try:
                length_val = int(row["length"])
            except ValueError:
                row_errors.append({"row": rownum, "field": "length", "message": "长度必须为整数"})

        precision_val = None
        if row.get("precision"):
            try:
                precision_val = int(row["precision"])
            except ValueError:
                row_errors.append({"row": rownum, "field": "precision", "message": "精度必须为整数"})

        if row_errors:
            errors.extend(row_errors)
            continue

        field = Field(
            field_code=row["field_code"],
            name=row["name"],
            english_name=row.get("english_name"),
            data_type=row["data_type"],
            length=length_val,
            precision=precision_val,
            table_name=row["table_name"],
            database_name=row.get("database_name"),
            business_domain=row.get("business_domain"),
            sensitivity_level=sl,
            description=row.get("description"),
            business_rules=row.get("business_rules"),
            source="excel_import",
            import_batch_id=import_record.id,
            created_by=user.id,
        )
        db.add(field)
        success += 1

    import_record.success_rows = success
    import_record.failed_rows = total - success
    import_record.status = "completed" if success == total else ("partial" if success > 0 else "failed")
    import_record.error_details = json.dumps(errors, ensure_ascii=False) if errors else None
    db.commit()
    db.refresh(import_record)
    return import_record


def export_fields_to_excel(fields: list[Field]) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "数据字段"
    ws.append(TEMPLATE_HEADERS + ["status", "is_anomaly"])

    for f in fields:
        ws.append([
            f.field_code, f.name, f.english_name, f.data_type, f.length,
            f.precision, f.table_name, f.database_name, f.business_domain,
            f.sensitivity_level, f.description, f.business_rules,
            f.status, str(f.is_anomaly),
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
