import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.checkpoint import CheckPoint
from app.models.checkpoint_event import CheckpointEvent, CheckpointEventBusinessType, CheckpointEventSource
from app.models.gate_event import Direction
from app.models.user import User, UserRole
from app.models.vehicle import Vehicle, VehicleStatus
from app.schemas.checkpoint_event import CheckpointEventCreate, CheckpointEventOut
from app.deps import get_current_user
from app.services.serial_numbers import generate_serial_no

router = APIRouter(prefix="/checkpoint-events", tags=["checkpoint-events"])


def _apply_scope(query, user: User):
    if user.role == UserRole.group_admin:
        return query
    if user.role == UserRole.factory_manager:
        return query.where(CheckpointEvent.factory_id == user.factory_id)
    query = query.where(CheckpointEvent.factory_id == user.factory_id)
    if user.department_id is not None:
        query = query.where(CheckpointEvent.department_id == user.department_id)
    return query


async def _serialize_checkpoint_events(
    db: AsyncSession,
    events: list[CheckpointEvent],
) -> list[CheckpointEventOut]:
    user_ids = {event.entered_by_user_id for event in events if event.entered_by_user_id is not None}
    user_name_map: dict[uuid.UUID, str] = {}
    if user_ids:
        user_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        user_name_map = {item.id: item.name for item in user_result.scalars().all()}

    return [
        CheckpointEventOut.model_validate(
            {
                **CheckpointEventOut.model_validate(event).model_dump(),
                "entered_by_user_name": user_name_map.get(event.entered_by_user_id) if event.entered_by_user_id else None,
            }
        )
        for event in events
    ]


@router.get("", response_model=list[CheckpointEventOut])
async def list_checkpoint_events(
    plate: str | None = Query(default=None),
    checkpoint_id: uuid.UUID | None = Query(default=None),
    department_id: uuid.UUID | None = Query(default=None),
    factory_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = _apply_scope(select(CheckpointEvent), user)
    if user.role == UserRole.group_admin and factory_id is not None:
        query = query.where(CheckpointEvent.factory_id == factory_id)
    if plate:
        query = query.where(CheckpointEvent.plate_number.ilike(f"%{plate}%"))
    if checkpoint_id is not None:
        query = query.where(CheckpointEvent.checkpoint_id == checkpoint_id)
    if department_id is not None:
        query = query.where(CheckpointEvent.department_id == department_id)
    result = await db.execute(query.order_by(CheckpointEvent.event_time.desc()))
    return await _serialize_checkpoint_events(db, list(result.scalars().all()))


@router.post("", response_model=CheckpointEventOut, status_code=201)
async def create_checkpoint_event(
    body: CheckpointEventCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    event_time = body.event_time or datetime.utcnow()
    checkpoint_result = await db.execute(select(CheckPoint).where(CheckPoint.id == body.checkpoint_id))
    checkpoint = checkpoint_result.scalar_one_or_none()
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    if user.role != UserRole.group_admin and checkpoint.factory_id != user.factory_id:
        raise HTTPException(status_code=403, detail="Checkpoint not in your factory")

    if user.role not in (UserRole.group_admin, UserRole.factory_manager):
        if checkpoint.department_id is None or checkpoint.department_id != user.department_id:
            raise HTTPException(status_code=403, detail="No permission to record this checkpoint")

    if body.business_type in (CheckpointEventBusinessType.delivery, CheckpointEventBusinessType.shipment) and not body.document_no:
        raise HTTPException(status_code=400, detail="送货和出货记录必须填写单号")

    latest_same_checkpoint_result = await db.execute(
        select(CheckpointEvent)
        .where(
            CheckpointEvent.factory_id == checkpoint.factory_id,
            CheckpointEvent.checkpoint_id == checkpoint.id,
            CheckpointEvent.plate_number == body.plate_number,
            CheckpointEvent.event_time <= event_time,
        )
        .order_by(CheckpointEvent.event_time.desc(), CheckpointEvent.created_at.desc())
        .limit(1)
    )
    latest_same_checkpoint_event = latest_same_checkpoint_result.scalar_one_or_none()
    if body.direction == Direction.entry and latest_same_checkpoint_event and latest_same_checkpoint_event.direction == Direction.entry:
        raise HTTPException(status_code=400, detail="同一节点不能连续入场，需先出场后再入场")

    vehicle_result = await db.execute(
        select(Vehicle).where(
            Vehicle.factory_id == checkpoint.factory_id,
            Vehicle.plate_number == body.plate_number,
        )
    )
    vehicle = vehicle_result.scalar_one_or_none()
    if vehicle is None:
        vehicle = Vehicle(
            serial_no=await generate_serial_no(
                db,
                model=Vehicle,
                serial_column=Vehicle.serial_no,
                module_prefix="VEH",
            ),
            factory_id=checkpoint.factory_id,
            plate_number=body.plate_number,
        )
        db.add(vehicle)
        await db.flush()

    vehicle.status = VehicleStatus.in_factory if body.direction.value == "entry" else VehicleStatus.out
    vehicle.last_seen_at = event_time
    vehicle.current_checkpoint_id = checkpoint.id

    event = CheckpointEvent(
        serial_no=await generate_serial_no(
            db,
            model=CheckpointEvent,
            serial_column=CheckpointEvent.serial_no,
            module_prefix="IO",
            at=event_time,
        ),
        factory_id=checkpoint.factory_id,
        checkpoint_id=checkpoint.id,
        department_id=checkpoint.department_id,
        vehicle_id=vehicle.id,
        plate_number=body.plate_number,
        direction=body.direction,
        event_time=event_time,
        source=CheckpointEventSource.manual,
        business_type=body.business_type,
        document_no=body.document_no,
        entered_by_user_id=user.id,
        note=body.note,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return (await _serialize_checkpoint_events(db, [event]))[0]
