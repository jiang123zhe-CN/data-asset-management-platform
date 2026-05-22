import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.operation_log import OperationLog
from app.schemas.log import OperationLogResponse
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/api/logs", tags=["Operation Logs"])


@router.get("/", response_model=PaginatedResponse[OperationLogResponse])
def list_logs(
    user_id: int | None = None,
    module: str | None = None,
    action: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("reviewer", "admin")),
):
    query = db.query(OperationLog)

    if user_id:
        query = query.filter(OperationLog.user_id == user_id)
    if module:
        query = query.filter(OperationLog.module == module)
    if action:
        query = query.filter(OperationLog.action == action)
    if date_from:
        query = query.filter(OperationLog.created_at >= date_from)
    if date_to:
        query = query.filter(OperationLog.created_at <= date_to + " 23:59:59")

    total = query.count()
    items = query.order_by(OperationLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[OperationLogResponse.model_validate(log) for log in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )
