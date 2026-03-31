import io
import uuid
from datetime import datetime, date
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.gate_event import GateEvent, Direction
from app.models.vehicle import Vehicle
from app.models.alert import Alert, AlertStatus
from app.models.user import User
from app.schemas.report import (
    TrafficReport, DailyTraffic, CheckpointTraffic,
    VehicleReport, VehicleActivity,
    AlertReport, AlertSummaryItem,
)
from app.deps import apply_data_scope, get_current_user, get_data_scope
import openpyxl

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/traffic", response_model=TrafficReport)
async def traffic_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    granularity: str = Query("day"),
    factory_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: str | list[uuid.UUID] = Depends(get_data_scope),
):
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    q = apply_data_scope(
        select(GateEvent).where(
            GateEvent.captured_at >= start_dt,
            GateEvent.captured_at <= end_dt,
        ),
        GateEvent.factory_id,
        scope,
        factory_id,
    )
    result = await db.execute(q)
    events = result.scalars().all()

    total_entries = sum(1 for e in events if e.direction == Direction.entry)
    total_exits = sum(1 for e in events if e.direction == Direction.exit)

    day_map: dict[str, dict] = {}
    for e in events:
        d = e.captured_at.strftime("%Y-%m-%d")
        if d not in day_map:
            day_map[d] = {"entries": 0, "exits": 0}
        if e.direction == Direction.entry:
            day_map[d]["entries"] += 1
        else:
            day_map[d]["exits"] += 1
    by_day = [DailyTraffic(date=d, **v) for d, v in sorted(day_map.items())]

    return TrafficReport(
        total_entries=total_entries,
        total_exits=total_exits,
        avg_stay_duration_minutes=None,
        by_day=by_day,
        by_checkpoint=[],
    )

@router.get("/vehicles", response_model=VehicleReport)
async def vehicle_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    factory_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: str | list[uuid.UUID] = Depends(get_data_scope),
):
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    q = apply_data_scope(
        select(GateEvent.vehicle_id, func.count().label("visits"))
        .where(
            GateEvent.captured_at >= start_dt,
            GateEvent.captured_at <= end_dt,
            GateEvent.vehicle_id.isnot(None),
        )
        .group_by(GateEvent.vehicle_id)
        .order_by(func.count().desc())
        .limit(50),
        GateEvent.factory_id,
        scope,
        factory_id,
    )
    result = await db.execute(q)
    rows = result.all()

    activities = []
    for vehicle_id, visits in rows:
        veh_result = await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
        vehicle = veh_result.scalar_one_or_none()
        alert_result = await db.execute(
            select(func.count()).where(
                Alert.vehicle_id == vehicle_id,
                Alert.created_at >= start_dt,
                Alert.created_at <= end_dt,
            )
        )
        alert_count = alert_result.scalar()
        if vehicle:
            activities.append(VehicleActivity(
                vehicle_id=str(vehicle_id),
                plate_number=vehicle.plate_number,
                total_visits=visits,
                alert_count=alert_count or 0,
            ))

    return VehicleReport(vehicles=activities)

@router.get("/alerts", response_model=AlertReport)
async def alert_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    factory_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: str | list[uuid.UUID] = Depends(get_data_scope),
):
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    q = apply_data_scope(
        select(Alert).where(
            Alert.created_at >= start_dt,
            Alert.created_at <= end_dt,
        ),
        Alert.factory_id,
        scope,
        factory_id,
    )
    result = await db.execute(q)
    alerts = result.scalars().all()

    total_active = sum(1 for a in alerts if a.status == AlertStatus.active)
    total_resolved = sum(1 for a in alerts if a.status == AlertStatus.resolved)

    type_map: dict[str, int] = {}
    for a in alerts:
        type_map[a.type.value] = type_map.get(a.type.value, 0) + 1
    by_type = [AlertSummaryItem(type=t, count=c) for t, c in type_map.items()]

    return AlertReport(total_active=total_active, total_resolved=total_resolved, by_type=by_type)

@router.get("/export")
async def export_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    format: str = Query("excel"),
    factory_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: str | list[uuid.UUID] = Depends(get_data_scope),
):
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    q = apply_data_scope(
        select(GateEvent).where(
            GateEvent.captured_at >= start_dt,
            GateEvent.captured_at <= end_dt,
        ).order_by(GateEvent.captured_at),
        GateEvent.factory_id,
        scope,
        factory_id,
    )
    result = await db.execute(q)
    events = result.scalars().all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "进出记录"
    ws.append(["车牌", "方向", "时间", "置信度", "审核状态"])
    for e in events:
        ws.append([
            e.plate_number,
            "入场" if e.direction == Direction.entry else "出场",
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
        headers={"Content-Disposition": f"attachment; filename=report_{start_date}_{end_date}.xlsx"},
    )
