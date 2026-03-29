from datetime import datetime, date
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.vehicle import Vehicle, VehicleStatus
from app.models.gate_event import GateEvent, ReviewStatus, Direction
from app.models.alert import Alert, AlertStatus
from app.models.user import User
from app.schemas.dashboard import DashboardStats
from app.deps import get_current_user
from app.ws.manager import manager

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    fid = user.factory_id
    today = datetime.combine(date.today(), datetime.min.time())

    in_factory = await db.scalar(
        select(func.count()).select_from(Vehicle).where(
            Vehicle.factory_id == fid, Vehicle.status == VehicleStatus.in_factory
        )
    )
    entries = await db.scalar(
        select(func.count()).select_from(GateEvent).where(
            GateEvent.factory_id == fid,
            GateEvent.direction == Direction.entry,
            GateEvent.captured_at >= today,
        )
    )
    exits = await db.scalar(
        select(func.count()).select_from(GateEvent).where(
            GateEvent.factory_id == fid,
            GateEvent.direction == Direction.exit,
            GateEvent.captured_at >= today,
        )
    )
    pending = await db.scalar(
        select(func.count()).select_from(GateEvent).where(
            GateEvent.factory_id == fid,
            GateEvent.review_status == ReviewStatus.pending_review,
        )
    )
    active_alerts = await db.scalar(
        select(func.count()).select_from(Alert).where(
            Alert.factory_id == fid, Alert.status == AlertStatus.active
        )
    )

    return DashboardStats(
        vehicles_in_factory=in_factory or 0,
        entries_today=entries or 0,
        exits_today=exits or 0,
        pending_review_count=pending or 0,
        active_alerts_count=active_alerts or 0,
    )

@router.websocket("/ws/{factory_id}")
async def websocket_endpoint(factory_id: str, websocket: WebSocket):
    await manager.connect(factory_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(factory_id, websocket)
