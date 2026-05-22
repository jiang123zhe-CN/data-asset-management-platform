import json

from sqlalchemy.orm import Session

from app.models.operation_log import OperationLog


def log_action(
    db: Session,
    *,
    user_id: int | None,
    username: str,
    action: str,
    module: str,
    target_type: str | None = None,
    target_id: int | None = None,
    detail: dict | None = None,
    ip_address: str | None = None,
):
    log = OperationLog(
        user_id=user_id,
        username=username,
        action=action,
        module=module,
        target_type=target_type,
        target_id=target_id,
        detail=json.dumps(detail, ensure_ascii=False) if detail else None,
        ip_address=ip_address,
    )
    db.add(log)
    db.commit()
