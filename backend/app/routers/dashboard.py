import uuid
from collections import defaultdict
from datetime import datetime, date
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.checkpoint import CheckPoint
from app.models.checkpoint_event import CheckpointEvent
from app.models.vehicle import Vehicle, VehicleStatus
from app.models.gate_event import GateEvent, ReviewStatus, Direction
from app.models.alert import Alert, AlertStatus
from app.models.user import User
from app.schemas.dashboard import DashboardRecentAccessNode, DashboardRecentAccessRecord, DashboardStats
from app.deps import apply_data_scope, get_current_user, get_data_scope
from app.ws.manager import manager

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _serialize_path_nodes(
    visit_events: list[CheckpointEvent],
    checkpoint_names: dict[uuid.UUID, str],
) -> list[DashboardRecentAccessNode]:
    return [
        DashboardRecentAccessNode(
            checkpoint_id=str(event.checkpoint_id),
            checkpoint_name=checkpoint_names.get(event.checkpoint_id, str(event.checkpoint_id)),
            event_time=event.event_time,
        )
        for event in visit_events
    ]


def _build_recent_access_records(
    events: list[CheckpointEvent],
    checkpoint_names: dict[uuid.UUID, str],
    limit: int,
) -> list[DashboardRecentAccessRecord]:
    grouped_events: dict[str, list[CheckpointEvent]] = defaultdict(list)
    for event in events:
        grouped_events[event.plate_number].append(event)

    records: list[DashboardRecentAccessRecord] = []
    for plate_number, plate_events in grouped_events.items():
        plate_events.sort(key=lambda item: item.event_time)
        current_visit: list[CheckpointEvent] = []

        for event in plate_events:
            if not current_visit:
                if event.direction == Direction.exit:
                    records.append(
                        DashboardRecentAccessRecord(
                            record_no=event.serial_no or f"IO{event.event_time:%Y%m%d%H%M%S}000",
                            plate_number=plate_number,
                            entry_time=None,
                            exit_time=event.event_time,
                            stay_duration_minutes=None,
                            status="exit_only",
                            path_nodes=_serialize_path_nodes([event], checkpoint_names),
                        )
                    )
                    continue
                current_visit = [event]
                continue

            current_visit.append(event)
            if event.direction != Direction.exit:
                continue

            first_event = current_visit[0]
            records.append(
                DashboardRecentAccessRecord(
                    record_no=first_event.serial_no or f"IO{first_event.event_time:%Y%m%d%H%M%S}000",
                    plate_number=plate_number,
                    entry_time=first_event.event_time,
                    exit_time=event.event_time,
                    stay_duration_minutes=max(int((event.event_time - first_event.event_time).total_seconds() // 60), 0),
                    status="completed",
                    path_nodes=_serialize_path_nodes(current_visit, checkpoint_names),
                )
            )
            current_visit = []

        if current_visit:
            now = datetime.utcnow()
            first_event = current_visit[0]
            records.append(
                DashboardRecentAccessRecord(
                    record_no=first_event.serial_no or f"IO{first_event.event_time:%Y%m%d%H%M%S}000",
                    plate_number=plate_number,
                    entry_time=first_event.event_time,
                    exit_time=None,
                    stay_duration_minutes=max(int((now - first_event.event_time).total_seconds() // 60), 0),
                    status="in_factory",
                    path_nodes=_serialize_path_nodes(current_visit, checkpoint_names),
                )
            )

    records.sort(
        key=lambda item: item.exit_time or item.entry_time or datetime.min,
        reverse=True,
    )
    return records[:limit]

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


@router.get("/recent-access-records", response_model=list[DashboardRecentAccessRecord])
async def get_recent_access_records(
    factory_id: uuid.UUID | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
    scope: str | list[uuid.UUID] = Depends(get_data_scope),
):
    query = apply_data_scope(
        select(CheckpointEvent).order_by(CheckpointEvent.event_time.desc()).limit(limit * 20),
        CheckpointEvent.factory_id,
        scope,
        factory_id,
    )
    result = await db.execute(query)
    events = list(result.scalars().all())
    checkpoint_ids = {event.checkpoint_id for event in events}
    checkpoint_names: dict[uuid.UUID, str] = {}
    if checkpoint_ids:
        checkpoint_result = await db.execute(select(CheckPoint).where(CheckPoint.id.in_(checkpoint_ids)))
        checkpoint_names = {checkpoint.id: checkpoint.name for checkpoint in checkpoint_result.scalars().all()}
    return _build_recent_access_records(events, checkpoint_names, limit)

@router.websocket("/ws/{factory_id}")
async def websocket_endpoint(factory_id: str, websocket: WebSocket):
    await manager.connect(factory_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(factory_id, websocket)
