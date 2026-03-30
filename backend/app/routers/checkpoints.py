import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.checkpoint import CheckPoint
from app.models.user import User, UserRole
from app.schemas.checkpoint import CheckPointCreate, CheckPointUpdate, CheckPointOut
from app.deps import get_current_user, require_roles

router = APIRouter(prefix="/checkpoints", tags=["checkpoints"])

@router.get("", response_model=list[CheckPointOut])
async def list_checkpoints(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CheckPoint).where(CheckPoint.factory_id == user.factory_id)
    )
    return result.scalars().all()

@router.post("", response_model=CheckPointOut, status_code=201)
async def create_checkpoint(
    body: CheckPointCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.factory_manager, UserRole.group_admin)),
):
    cp = CheckPoint(**body.model_dump(), factory_id=user.factory_id)
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
    result = await db.execute(
        select(CheckPoint).where(CheckPoint.id == cp_id, CheckPoint.factory_id == user.factory_id)
    )
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
    result = await db.execute(
        select(CheckPoint).where(CheckPoint.id == cp_id, CheckPoint.factory_id == user.factory_id)
    )
    cp = result.scalar_one_or_none()
    if not cp:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    await db.delete(cp)
    await db.commit()
