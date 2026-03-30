import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models.gate_event import GateEvent, ReviewStatus, Direction
from app.models.vehicle import Vehicle, VehicleStatus
from app.models.user import User, UserRole
from app.schemas.gate_event import GateEventCreate, GateEventOut, ReviewRequest
from app.deps import get_current_user, require_roles
from app.config import settings
import openpyxl
import io

router = APIRouter(prefix="/gate-events", tags=["gate-events"])

@router.get("", response_model=list[GateEventOut])
async def list_gate_events(
    plate: str | None = Query(None),
    direction: Direction | None = Query(None),
    review_status: ReviewStatus | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(GateEvent).where(GateEvent.factory_id == user.factory_id)
    if plate:
        q = q.where(GateEvent.plate_number.ilike(f"%{plate}%"))
    if direction:
        q = q.where(GateEvent.direction == direction)
    if review_status:
        q = q.where(GateEvent.review_status == review_status)
    q = q.order_by(desc(GateEvent.captured_at)).offset(offset).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()

@router.get("/export")
async def export_gate_events(
    plate: str | None = Query(None),
    direction: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(GateEvent).where(GateEvent.factory_id == user.factory_id)
    if plate:
        q = q.where(GateEvent.plate_number.ilike(f"%{plate}%"))
    if direction:
        q = q.where(GateEvent.direction == direction)
    q = q.order_by(desc(GateEvent.captured_at)).limit(10000)
    result = await db.execute(q)
    events = result.scalars().all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "出入记录"
    ws.append(["车牌", "方向", "时间", "置信度", "审核状态"])
    for e in events:
        ws.append([
            e.plate_number,
            "入场" if e.direction.value == "entry" else "出场",
            e.captured_at.strftime("%Y-%m-%d %H:%M:%S"),
            f"{e.confidence_score:.2%}" if e.confidence_score else "",
            e.review_status.value,
        ])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=gate_events.xlsx"},
    )

@router.post("", response_model=GateEventOut)
async def create_gate_event(
    body: GateEventCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Called by AI recognition service only (internal network).
    No user auth required — protected by network isolation in Docker Compose.
    """
    review_status = (
        ReviewStatus.auto_confirmed
        if (body.confidence_score or 0) >= settings.ai_confidence_threshold
        else ReviewStatus.pending_review
    )
    event = GateEvent(
        factory_id=body.factory_id,
        gate_id=body.gate_id,
        plate_number=body.plate_number,
        direction=body.direction,
        image_url=body.image_url,
        confidence_score=body.confidence_score,
        review_status=review_status,
    )

    result = await db.execute(
        select(Vehicle).where(
            Vehicle.plate_number == body.plate_number,
            Vehicle.factory_id == body.factory_id,
        )
    )
    vehicle = result.scalar_one_or_none()
    if vehicle:
        event.vehicle_id = vehicle.id
        vehicle.status = VehicleStatus.in_factory if body.direction.value == "entry" else VehicleStatus.out
        vehicle.last_seen_at = datetime.utcnow()

    db.add(event)
    await db.commit()
    await db.refresh(event)

    if review_status == ReviewStatus.pending_review:
        from app.services.alert_engine import create_pending_review_alert
        await create_pending_review_alert(db, body.factory_id, body.plate_number)

    # Async broadcast (non-blocking, best-effort)
    try:
        from app.ws.manager import manager
        import asyncio
        asyncio.create_task(manager.broadcast(str(body.factory_id), {
            "type": "gate_event",
            "plate_number": body.plate_number,
            "direction": body.direction.value,
            "review_status": review_status.value,
        }))
    except Exception:
        pass

    return event

@router.patch("/{event_id}/review", response_model=GateEventOut)
async def review_gate_event(
    event_id: uuid.UUID,
    body: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.operator, UserRole.factory_manager, UserRole.group_admin)),
):
    result = await db.execute(select(GateEvent).where(GateEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.plate_number = body.plate_number
    event.review_status = (
        ReviewStatus.manually_confirmed if body.action == "confirm" else ReviewStatus.rejected
    )
    event.reviewed_by = user.id
    event.reviewed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(event)
    return event

class BatchReviewRequest(BaseModel):
    ids: list[uuid.UUID]
    action: str  # "confirm" or "reject"

class BatchReviewResponse(BaseModel):
    updated: int

@router.post("/batch-review", response_model=BatchReviewResponse)
async def batch_review_gate_events(
    body: BatchReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.operator, UserRole.factory_manager, UserRole.group_admin)),
):
    result = await db.execute(
        select(GateEvent).where(
            GateEvent.id.in_(body.ids),
            GateEvent.factory_id == user.factory_id,
            GateEvent.review_status == ReviewStatus.pending_review,
        )
    )
    events = result.scalars().all()
    new_status = ReviewStatus.manually_confirmed if body.action == "confirm" else ReviewStatus.rejected
    for event in events:
        event.review_status = new_status
        event.reviewed_by = user.id
        event.reviewed_at = datetime.utcnow()
    await db.commit()
    return BatchReviewResponse(updated=len(events))
