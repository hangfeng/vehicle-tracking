import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.vehicle_journey import VehicleJourney, JourneyEvent, JourneyStatus
from app.models.path_template import PathTemplateStep
from app.models.vehicle import Vehicle
from app.models.alert import Alert, AlertType, AlertSeverity, AlertStatus
from app.models.user import User
from app.schemas.vehicle_journey import VehicleJourneyCreate, JourneyEventCreate, VehicleJourneyOut, JourneyEventOut
from app.deps import get_current_user

router = APIRouter(tags=["vehicle-journeys"])

@router.post("/vehicle-journeys", response_model=VehicleJourneyOut, status_code=201)
async def start_journey(
    body: VehicleJourneyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Close any existing active journey for this vehicle
    result = await db.execute(
        select(VehicleJourney).where(
            VehicleJourney.vehicle_id == body.vehicle_id,
            VehicleJourney.status == JourneyStatus.active,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.status = JourneyStatus.completed
        existing.completed_at = datetime.utcnow()

    journey = VehicleJourney(
        vehicle_id=body.vehicle_id,
        factory_id=body.factory_id,
        template_id=body.template_id,
    )
    db.add(journey)
    await db.commit()
    await db.refresh(journey)
    return journey

@router.get("/vehicles/{vehicle_id}/journey", response_model=VehicleJourneyOut | None)
async def get_active_journey(
    vehicle_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(VehicleJourney).where(
            VehicleJourney.vehicle_id == vehicle_id,
            VehicleJourney.status == JourneyStatus.active,
        )
    )
    return result.scalar_one_or_none()

@router.get("/vehicles/{vehicle_id}/journeys", response_model=list[VehicleJourneyOut])
async def list_journeys(
    vehicle_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(VehicleJourney).where(VehicleJourney.vehicle_id == vehicle_id)
    )
    return result.scalars().all()

@router.post("/journey-events", response_model=JourneyEventOut, status_code=201)
async def record_journey_event(
    body: JourneyEventCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(VehicleJourney).where(VehicleJourney.id == body.journey_id))
    journey = result.scalar_one_or_none()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    is_deviation = False

    if journey.template_id:
        # Deviation = checkpoint not in template, or direction mismatch
        steps_result = await db.execute(
            select(PathTemplateStep).where(PathTemplateStep.template_id == journey.template_id)
        )
        steps = steps_result.scalars().all()
        # Build map: checkpoint_id -> expected direction
        template_map = {s.checkpoint_id: s.direction for s in steps}

        if body.checkpoint_id not in template_map:
            is_deviation = True
        else:
            expected_dir = template_map[body.checkpoint_id]
            if expected_dir.value != "any" and expected_dir.value != body.direction.value:
                is_deviation = True

    event = JourneyEvent(
        journey_id=body.journey_id,
        checkpoint_id=body.checkpoint_id,
        direction=body.direction,
        is_deviation=is_deviation,
        notes=body.notes,
    )
    db.add(event)

    if is_deviation:
        journey.status = JourneyStatus.deviated
        veh_result = await db.execute(select(Vehicle).where(Vehicle.id == journey.vehicle_id))
        vehicle = veh_result.scalar_one_or_none()
        alert = Alert(
            factory_id=journey.factory_id,
            vehicle_id=journey.vehicle_id,
            type=AlertType.path_deviation,
            message=f"车辆 {vehicle.plate_number if vehicle else '未知'} 偏离预定路径",
            severity=AlertSeverity.warning,
            status=AlertStatus.active,
        )
        db.add(alert)

    # Update vehicle current checkpoint
    veh_result = await db.execute(select(Vehicle).where(Vehicle.id == journey.vehicle_id))
    vehicle = veh_result.scalar_one_or_none()
    if vehicle:
        vehicle.current_checkpoint_id = body.checkpoint_id

    await db.commit()
    await db.refresh(event)
    return event
