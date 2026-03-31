import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, union_all
from app.database import get_db
from app.models.factory import Factory
from app.models.alert import Alert
from app.models.checkpoint import CheckPoint
from app.models.gate_event import GateEvent
from app.models.location import Location
from app.models.path_template import PathTemplate
from app.models.user import User, UserRole
from app.models.vehicle import Vehicle
from app.models.vehicle_journey import VehicleJourney
from app.schemas.factory import FactoryCreate, FactoryUpdate, FactoryOut
from app.deps import require_roles

router = APIRouter(prefix="/factories", tags=["factories"])


async def _list_inferred_factory_ids(db: AsyncSession) -> list[uuid.UUID]:
    factory_id_sources = union_all(
        select(User.factory_id.label("factory_id")).where(User.factory_id.isnot(None)),
        select(CheckPoint.factory_id.label("factory_id")),
        select(PathTemplate.factory_id.label("factory_id")),
        select(Vehicle.factory_id.label("factory_id")),
        select(GateEvent.factory_id.label("factory_id")),
        select(Alert.factory_id.label("factory_id")),
        select(Location.factory_id.label("factory_id")),
        select(VehicleJourney.factory_id.label("factory_id")),
    ).subquery()

    result = await db.execute(
        select(factory_id_sources.c.factory_id).distinct()
    )
    return list(result.scalars().all())


@router.get("", response_model=list[FactoryOut])
async def list_factories(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.group_admin)),
):
    result = await db.execute(select(Factory).order_by(Factory.created_at))
    factories = list(result.scalars().all())

    existing_ids = {factory.id for factory in factories}
    inferred_ids = await _list_inferred_factory_ids(db)
    inferred_factories = [
        FactoryOut(
            id=factory_id,
            name=f"厂区 {str(factory_id)[:8]}",
            address=None,
            timezone="Asia/Shanghai",
            is_active=True,
            created_at=datetime.utcnow(),
        )
        for factory_id in inferred_ids
        if factory_id not in existing_ids
    ]

    return [FactoryOut.model_validate(factory) for factory in factories] + inferred_factories


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
