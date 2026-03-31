import uuid
from datetime import datetime, date
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.vehicle import Vehicle, VehicleStatus
from app.models.gate_event import GateEvent, ReviewStatus, Direction
from app.models.alert import Alert, AlertStatus
from app.models.user import User
from app.schemas.dashboard import DashboardStats
from app.deps import apply_data_scope, get_current_user, get_data_scope
from app.ws.manager import manager

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    factory_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: str | list[uuid.UUID] = Depends(get_data_scope),
):
    today = datetime.combine(date.today(), datetime.min.time())

    in_factory = await db.scalar(
        apply_data_scope(
            select(func.count()).select_from(Vehicle).where(Vehicle.status == VehicleStatus.in_factory),
            Vehicle.factory_id,
            scope,
            factory_id,
        )
    )
    entries = await db.scalar(
        apply_data_scope(
            select(func.count()).select_from(GateEvent).where(
                GateEvent.direction == Direction.entry,
                GateEvent.captured_at >= today,
            ),
            GateEvent.factory_id,
            scope,
            factory_id,
        )
    )
    exits = await db.scalar(
        apply_data_scope(
            select(func.count()).select_from(GateEvent).where(
                GateEvent.direction == Direction.exit,
                GateEvent.captured_at >= today,
            ),
            GateEvent.factory_id,
            scope,
            factory_id,
        )
    )
    pending = await db.scalar(
        apply_data_scope(
            select(func.count()).select_from(GateEvent).where(
                GateEvent.review_status == ReviewStatus.pending_review,
            ),
            GateEvent.factory_id,
            scope,
            factory_id,
        )
    )
    active_alerts = await db.scalar(
        apply_data_scope(
            select(func.count()).select_from(Alert).where(Alert.status == AlertStatus.active),
            Alert.factory_id,
            scope,
            factory_id,
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
