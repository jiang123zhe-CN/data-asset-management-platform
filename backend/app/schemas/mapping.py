from datetime import datetime
from pydantic import BaseModel


class MappingCreate(BaseModel):
    directory_id: int
    field_id: int
    mapping_type: str = "direct"


class MappingBatchCreate(BaseModel):
    directory_id: int
    field_ids: list[int]


class MappingBatchDelete(BaseModel):
    mapping_ids: list[int]


class MappingResponse(BaseModel):
    id: int
    directory_id: int
    field_id: int
    mapping_type: str
    mapping_source: str
    confidence: float | None = None
    created_by: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MappingDetailResponse(BaseModel):
    id: int
    directory_id: int
    directory_name: str | None = None
    directory_code: str | None = None
    directory_path: str | None = None
    field_id: int
    field_code: str | None = None
    field_name: str | None = None
    field_data_type: str | None = None
    field_table: str | None = None
    mapping_type: str
    mapping_source: str
    confidence: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class VisualizationNode(BaseModel):
    id: str
    label: str
    node_type: str  # "directory" or "field"
    group: str | None = None


class VisualizationEdge(BaseModel):
    source: str
    target: str
    label: str | None = None


class VisualizationData(BaseModel):
    nodes: list[VisualizationNode]
    edges: list[VisualizationEdge]


class AutoMapTaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


class AutoMapResultResponse(BaseModel):
    task_id: str
    status: str
    total_fields: int
    mapped_count: int
    results: list[dict]
