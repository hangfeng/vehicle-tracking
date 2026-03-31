import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.factory import Factory
from app.models.user import User, UserRole
from app.schemas.factory import FactoryCreate, FactoryUpdate, FactoryOut
from app.deps import require_roles

router = APIRouter(prefix="/factories", tags=["factories"])


@router.get("", response_model=list[FactoryOut])
async def list_factories(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.group_admin)),
):
    result = await db.execute(select(Factory).order_by(Factory.created_at))
    return result.scalars().all()


@router.post("", response_model=FactoryOut, status_code=201)
async def create_factory(
    body: FactoryCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.group_admin)),
):
    factory = Factory(**body.model_dump())
    db.add(factory)
    await db.commit()
    await db.refresh(factory)
    return factory


@router.patch("/{factory_id}", response_model=FactoryOut)
async def update_factory(
    factory_id: uuid.UUID,
    body: FactoryUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.group_admin)),
):
    result = await db.execute(select(Factory).where(Factory.id == factory_id))
    factory = result.scalar_one_or_none()
    if not factory:
        raise HTTPException(status_code=404, detail="Factory not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(factory, k, v)
    await db.commit()
    await db.refresh(factory)
    return factory


@router.delete("/{factory_id}", status_code=204)
async def delete_factory(
    factory_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.group_admin)),
):
    result = await db.execute(select(Factory).where(Factory.id == factory_id))
    factory = result.scalar_one_or_none()
    if not factory:
        raise HTTPException(status_code=404, detail="Factory not found")
    await db.delete(factory)
    await db.commit()
