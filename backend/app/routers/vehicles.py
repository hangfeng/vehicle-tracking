import uuid
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import openpyxl
from app.database import get_db
from app.models.vehicle import Vehicle, VehicleStatus
from app.models.user import User, UserRole
from app.schemas.vehicle import VehicleCreate, VehicleUpdate, VehicleOut
from app.deps import get_current_user, require_roles
from app.services.serial_numbers import generate_serial_no

router = APIRouter(prefix="/vehicles", tags=["vehicles"])

def _resolve_factory_id(user: User, provided: uuid.UUID | None) -> uuid.UUID:
    if user.role == UserRole.group_admin:
        if not provided:
            raise HTTPException(status_code=400, detail="集团管理员需指定 factory_id")
        return provided
    return user.factory_id


@router.get("", response_model=list[VehicleOut])
async def list_vehicles(
    factory_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == UserRole.group_admin:
        query = select(Vehicle)
        if factory_id:
            query = query.where(Vehicle.factory_id == factory_id)
    else:
        query = select(Vehicle).where(Vehicle.factory_id == user.factory_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/in-factory-candidates", response_model=list[VehicleOut])
async def list_in_factory_candidates(
    factory_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == UserRole.group_admin:
        query = select(Vehicle).where(Vehicle.status == VehicleStatus.in_factory)
        if factory_id:
            query = query.where(Vehicle.factory_id == factory_id)
    else:
        query = select(Vehicle).where(
            Vehicle.factory_id == user.factory_id,
            Vehicle.status == VehicleStatus.in_factory,
        )
    result = await db.execute(query.order_by(Vehicle.last_seen_at.desc().nullslast(), Vehicle.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=VehicleOut)
async def create_vehicle(
    body: VehicleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.factory_manager, UserRole.group_admin)),
):
    fid = _resolve_factory_id(user, body.factory_id)
    data = body.model_dump(exclude={"factory_id"})
    vehicle = Vehicle(
        **data,
        factory_id=fid,
        serial_no=await generate_serial_no(
            db,
            model=Vehicle,
            serial_column=Vehicle.serial_no,
            module_prefix="VEH",
        ),
    )
    db.add(vehicle)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle

class ImportResponse(BaseModel):
    created: int
    skipped: int
    errors: list[str]

@router.post("/import", response_model=ImportResponse)
async def import_vehicles(
    file: UploadFile = File(...),
    factory_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.factory_manager, UserRole.group_admin)),
):
    fid = _resolve_factory_id(user, factory_id)
    content = await file.read()
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Excel file")

    ws = wb.active
    created = 0
    skipped = 0
    errors = []

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or not row[0]:
            continue
        plate = str(row[0]).strip()
        company = str(row[1]).strip() if len(row) > 1 and row[1] else None
        contact_name = str(row[2]).strip() if len(row) > 2 and row[2] else None
        contact_phone = str(row[3]).strip() if len(row) > 3 and row[3] else None

        if not plate:
            errors.append(f"Row {row_idx}: 车牌号不能为空")
            continue
        if not company:
            errors.append(f"Row {row_idx}: 所属公司不能为空")
            continue

        existing = await db.execute(
            select(Vehicle).where(Vehicle.plate_number == plate, Vehicle.factory_id == fid)
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        vehicle = Vehicle(
            serial_no=await generate_serial_no(
                db,
                model=Vehicle,
                serial_column=Vehicle.serial_no,
                module_prefix="VEH",
            ),
            plate_number=plate,
            company=company,
            contact_name=contact_name,
            contact_phone=contact_phone,
            factory_id=fid,
        )
        db.add(vehicle)
        await db.flush()
        created += 1

    await db.commit()
    return ImportResponse(created=created, skipped=skipped, errors=errors)

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
