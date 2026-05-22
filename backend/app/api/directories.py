from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.directory import Directory
from app.schemas.directory import (
    DirectoryCreate,
    DirectoryUpdate,
    DirectoryMove,
    DirectoryResponse,
    DirectoryTreeNode,
)

router = APIRouter(prefix="/api/directories", tags=["Directories"])


def _build_tree_node(dir: Directory, db: Session) -> DirectoryTreeNode:
    children_count = db.query(Directory).filter(
        Directory.parent_id == dir.id, Directory.is_active == True
    ).count()
    field_count = 0  # Will be updated in Phase 4
    return DirectoryTreeNode(
        id=dir.id,
        name=dir.name,
        code=dir.code,
        parent_id=dir.parent_id,
        level=dir.level,
        children_count=children_count,
        field_count=field_count,
    )


@router.get("/tree", response_model=list[DirectoryTreeNode])
def get_tree(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    dirs = db.query(Directory).filter(Directory.is_active == True).order_by(Directory.level, Directory.sort_order).all()
    return [_build_tree_node(d, db) for d in dirs]


@router.get("/{dir_id}", response_model=DirectoryResponse)
def get_directory(dir_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    dir = db.query(Directory).filter(Directory.id == dir_id, Directory.is_active == True).first()
    if not dir:
        raise HTTPException(status_code=404, detail="Directory not found")
    return dir


@router.post("/", response_model=DirectoryResponse, status_code=201)
def create_directory(
    body: DirectoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("system_admin", "admin")),
):
    if db.query(Directory).filter(Directory.code == body.code).first():
        raise HTTPException(status_code=400, detail="Code already exists")

    if body.parent_id:
        parent = db.query(Directory).filter(Directory.id == body.parent_id, Directory.is_active == True).first()
        if not parent:
            raise HTTPException(status_code=400, detail="Parent directory not found")
        level = parent.level + 1
    else:
        level = 0

    dir = Directory(
        name=body.name,
        code=body.code,
        description=body.description,
        tags=body.tags,
        parent_id=body.parent_id,
        level=level,
        sort_order=body.sort_order,
        created_by=current_user.id,
    )
    db.add(dir)
    db.commit()
    db.refresh(dir)
    return dir


@router.put("/{dir_id}", response_model=DirectoryResponse)
def update_directory(
    dir_id: int,
    body: DirectoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("system_admin", "admin")),
):
    dir = db.query(Directory).filter(Directory.id == dir_id, Directory.is_active == True).first()
    if not dir:
        raise HTTPException(status_code=404, detail="Directory not found")

    if body.code and body.code != dir.code:
        if db.query(Directory).filter(Directory.code == body.code).first():
            raise HTTPException(status_code=400, detail="Code already exists")
        dir.code = body.code

    if body.name is not None:
        dir.name = body.name
    if body.description is not None:
        dir.description = body.description
    if body.tags is not None:
        dir.tags = body.tags
    if body.parent_id is not None and body.parent_id != dir.parent_id:
        if body.parent_id == dir_id:
            raise HTTPException(status_code=400, detail="Cannot set self as parent")
        new_level = 0
        if body.parent_id:
            parent = db.query(Directory).filter(Directory.id == body.parent_id, Directory.is_active == True).first()
            if not parent:
                raise HTTPException(status_code=400, detail="Parent directory not found")
            new_level = parent.level + 1
        dir.parent_id = body.parent_id
        dir.level = new_level
    if body.sort_order is not None:
        dir.sort_order = body.sort_order

    dir.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(dir)
    return dir


@router.delete("/{dir_id}")
def delete_directory(
    dir_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("system_admin", "admin")),
):
    dir = db.query(Directory).filter(Directory.id == dir_id, Directory.is_active == True).first()
    if not dir:
        raise HTTPException(status_code=404, detail="Directory not found")

    children = db.query(Directory).filter(Directory.parent_id == dir_id, Directory.is_active == True).count()
    if children > 0:
        raise HTTPException(status_code=400, detail="Cannot delete directory with children")

    dir.is_active = False
    db.commit()
    return {"message": "Directory deleted"}


@router.put("/{dir_id}/move", response_model=DirectoryResponse)
def move_directory(
    dir_id: int,
    body: DirectoryMove,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("system_admin", "admin")),
):
    dir = db.query(Directory).filter(Directory.id == dir_id, Directory.is_active == True).first()
    if not dir:
        raise HTTPException(status_code=404, detail="Directory not found")

    if body.parent_id == dir_id:
        raise HTTPException(status_code=400, detail="Cannot set self as parent")

    new_level = 0
    if body.parent_id:
        parent = db.query(Directory).filter(Directory.id == body.parent_id, Directory.is_active == True).first()
        if not parent:
            raise HTTPException(status_code=400, detail="Parent directory not found")
        new_level = parent.level + 1

    dir.parent_id = body.parent_id
    dir.level = new_level
    dir.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(dir)
    return dir
