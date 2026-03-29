import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.vehicle import Vehicle
from app.models.user import User, UserRole
from app.schemas.vehicle import VehicleCreate, VehicleUpdate, VehicleOut
from app.deps import get_current_user, require_roles

router = APIRouter(prefix="/vehicles", tags=["vehicles"])

@router.get("", response_model=list[VehicleOut])
async def list_vehicles(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Vehicle).where(Vehicle.factory_id == user.factory_id)
    )
    return result.scalars().all()

@router.post("", response_model=VehicleOut)
async def create_vehicle(
    body: VehicleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.factory_manager, UserRole.group_admin)),
):
    vehicle = Vehicle(**body.model_dump(), factory_id=user.factory_id)
    db.add(vehicle)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle

@router.patch("/{vehicle_id}", response_model=VehicleOut)
async def update_vehicle(
    vehicle_id: uuid.UUID,
    body: VehicleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.factory_manager, UserRole.group_admin)),
):
    result = await db.execute(
        select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.factory_id == user.factory_id)
    )
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(vehicle, k, v)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle
