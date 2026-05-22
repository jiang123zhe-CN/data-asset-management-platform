from datetime import datetime
from pydantic import BaseModel, Field


class DirectoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=100)
    description: str | None = None
    tags: str | None = None
    parent_id: int | None = None
    sort_order: int = 0


class DirectoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    code: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    tags: str | None = None
    parent_id: int | None = None
    sort_order: int | None = None


class DirectoryMove(BaseModel):
    parent_id: int | None = None


class DirectoryResponse(BaseModel):
    id: int
    name: str
    code: str
    description: str | None = None
    tags: str | None = None
    parent_id: int | None = None
    level: int
    sort_order: int
    is_active: bool
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DirectoryTreeNode(BaseModel):
    id: int
    name: str
    code: str
    parent_id: int | None = None
    level: int
    children_count: int = 0
    field_count: int = 0
