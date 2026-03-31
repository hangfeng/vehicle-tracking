import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.checkpoint import CheckPoint
from app.models.user import User, UserRole
from app.schemas.checkpoint import CheckPointCreate, CheckPointUpdate, CheckPointOut
from app.deps import apply_data_scope, get_current_user, get_data_scope, require_roles

router = APIRouter(prefix="/checkpoints", tags=["checkpoints"])


def _resolve_factory_id(user: User, provided: uuid.UUID | None) -> uuid.UUID:
    """集团管理员必须提供 factory_id；厂区管理员使用自己的 factory_id。"""
    if user.role == UserRole.group_admin:
        if not provided:
            raise HTTPException(status_code=400, detail="集团管理员需指定 factory_id")
        return provided
    return user.factory_id


@router.get("", response_model=list[CheckPointOut])
async def list_checkpoints(
    factory_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: str | list[uuid.UUID] = Depends(get_data_scope),
):
    query = apply_data_scope(select(CheckPoint), CheckPoint.factory_id, scope, factory_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=CheckPointOut, status_code=201)
async def create_checkpoint(
    body: CheckPointCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.factory_manager, UserRole.group_admin)),
):
    fid = _resolve_factory_id(user, body.factory_id)
    data = body.model_dump(exclude={"factory_id"})
    cp = CheckPoint(**data, factory_id=fid)
    db.add(cp)
    await db.commit()
    await db.refresh(cp)
    return cp


@router.patch("/{cp_id}", response_model=CheckPointOut)
async def update_checkpoint(
    cp_id: uuid.UUID,
    body: CheckPointUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.factory_manager, UserRole.group_admin)),
):
    query = select(CheckPoint).where(CheckPoint.id == cp_id)
    if user.role != UserRole.group_admin:
        query = query.where(CheckPoint.factory_id == user.factory_id)
    result = await db.execute(query)
    cp = result.scalar_one_or_none()
    if not cp:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(cp, k, v)
    await db.commit()
    await db.refresh(cp)
    return cp


@router.delete("/{cp_id}", status_code=204)
async def delete_checkpoint(
    cp_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.factory_manager, UserRole.group_admin)),
):
    query = select(CheckPoint).where(CheckPoint.id == cp_id)
    if user.role != UserRole.group_admin:
        query = query.where(CheckPoint.factory_id == user.factory_id)
    result = await db.execute(query)
    cp = result.scalar_one_or_none()
    if not cp:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    await db.delete(cp)
    await db.commit()
