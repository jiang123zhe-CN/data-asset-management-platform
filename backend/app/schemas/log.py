from datetime import datetime
from pydantic import BaseModel


class OperationLogResponse(BaseModel):
    id: int
    user_id: int | None = None
    username: str
    action: str
    module: str
    target_type: str | None = None
    target_id: int | None = None
    detail: str | None = None
    ip_address: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
