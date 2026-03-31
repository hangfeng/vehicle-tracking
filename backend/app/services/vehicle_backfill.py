from datetime import datetime
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gate_event import Direction, GateEvent
from app.models.vehicle import Vehicle, VehicleStatus
from app.services.serial_numbers import generate_serial_no


async def backfill_vehicles_from_gate_events(db: AsyncSession) -> int:
    latest_events = (
        select(
            GateEvent.factory_id,
            GateEvent.plate_number,
            func.max(GateEvent.captured_at).label("latest_captured_at"),
        )
        .group_by(GateEvent.factory_id, GateEvent.plate_number)
        .subquery()
    )

    result = await db.execute(
        select(GateEvent)
        .join(
            latest_events,
            (GateEvent.factory_id == latest_events.c.factory_id)
            & (GateEvent.plate_number == latest_events.c.plate_number)
            & (GateEvent.captured_at == latest_events.c.latest_captured_at),
        )
    )
    created = 0

    for event in result.scalars().all():
        existing = await db.execute(
            select(Vehicle).where(
                Vehicle.factory_id == event.factory_id,
                Vehicle.plate_number == event.plate_number,
            )
        )
        if existing.scalar_one_or_none():
            continue

        vehicle = Vehicle(
            serial_no=await generate_serial_no(
                db,
                model=Vehicle,
                serial_column=Vehicle.serial_no,
                module_prefix="VEH",
                at=event.captured_at or datetime.utcnow(),
            ),
            factory_id=event.factory_id,
            plate_number=event.plate_number,
            status=VehicleStatus.in_factory if event.direction == Direction.entry else VehicleStatus.out,
            last_seen_at=event.captured_at or datetime.utcnow(),
        )
        db.add(vehicle)
        await db.flush()
        created += 1

    await db.commit()
    return created
