import io
import uuid
from datetime import datetime, date
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.checkpoint import CheckPoint
from app.models.checkpoint_event import CheckpointEvent, CheckpointEventBusinessType, CheckpointEventSource
from app.models.department import Department
from app.models.factory import Factory
from app.models.gate_event import GateEvent, Direction
from app.models.vehicle import Vehicle
from app.models.alert import Alert, AlertStatus
from app.models.user import User, UserRole
from app.schemas.report import (
    TrafficReport, DailyTraffic, CheckpointTraffic,
    VehicleReport, VehicleActivity,
    AlertReport, AlertSummaryItem,
    AccessDetailRow,
    UserDetailRow,
    VehicleDetailRow,
)
from app.deps import apply_data_scope, get_current_user, get_data_scope
import openpyxl

router = APIRouter(prefix="/reports", tags=["reports"])


def _traffic_bucket_label(value: datetime, granularity: str) -> str:
    if granularity == "week":
        week_start = value.date().fromordinal(value.date().toordinal() - value.weekday())
        return week_start.strftime("%Y-%m-%d")
    if granularity == "month":
        return value.strftime("%Y-%m")
    return value.strftime("%Y-%m-%d")


def _apply_checkpoint_event_scope(query, user: User):
    if user.role == UserRole.group_admin:
        return query
    if user.role == UserRole.factory_manager:
        return query.where(CheckpointEvent.factory_id == user.factory_id)
    query = query.where(CheckpointEvent.factory_id == user.factory_id)
    if user.department_id is not None:
        query = query.where(CheckpointEvent.department_id == user.department_id)
    return query


async def _build_access_detail_rows(
    db: AsyncSession,
    events: list[CheckpointEvent],
) -> list[AccessDetailRow]:
    checkpoint_ids = {event.checkpoint_id for event in events}
    department_ids = {event.department_id for event in events if event.department_id is not None}
    user_ids = {event.entered_by_user_id for event in events if event.entered_by_user_id is not None}

    checkpoint_map: dict[uuid.UUID, str] = {}
    department_map: dict[uuid.UUID, str] = {}
    user_map: dict[uuid.UUID, str] = {}

    if checkpoint_ids:
        checkpoint_result = await db.execute(select(CheckPoint).where(CheckPoint.id.in_(checkpoint_ids)))
        checkpoint_map = {item.id: item.name for item in checkpoint_result.scalars().all()}
    if department_ids:
        department_result = await db.execute(select(Department).where(Department.id.in_(department_ids)))
        department_map = {item.id: item.name for item in department_result.scalars().all()}
    if user_ids:
        user_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        user_map = {item.id: item.name for item in user_result.scalars().all()}

    return [
        AccessDetailRow(
            serial_no=event.serial_no,
            event_time=event.event_time.isoformat(),
            plate_number=event.plate_number,
            direction=event.direction.value,
            checkpoint_name=checkpoint_map.get(event.checkpoint_id, str(event.checkpoint_id)),
            department_name=department_map.get(event.department_id) if event.department_id else None,
            business_type=event.business_type.value,
            document_no=event.document_no,
            source=event.source.value,
            entered_by_user_name=user_map.get(event.entered_by_user_id) if event.entered_by_user_id else None,
            note=event.note,
        )
        for event in events
    ]


async def _build_vehicle_detail_rows(
    vehicles: list[Vehicle],
) -> list[VehicleDetailRow]:
    return [
        VehicleDetailRow(
            serial_no=vehicle.serial_no,
            plate_number=vehicle.plate_number,
            vehicle_type=vehicle.vehicle_type,
            company=vehicle.company,
            contact_name=vehicle.contact_name,
            contact_phone=vehicle.contact_phone,
            status=vehicle.status.value,
            last_seen_at=vehicle.last_seen_at.isoformat() if vehicle.last_seen_at else None,
            note=vehicle.note,
        )
        for vehicle in vehicles
    ]


async def _build_user_detail_rows(
    db: AsyncSession,
    users: list[User],
) -> list[UserDetailRow]:
    factory_ids = {user.factory_id for user in users if user.factory_id is not None}
    department_ids = {user.department_id for user in users if user.department_id is not None}

    factory_map: dict[uuid.UUID, str] = {}
    department_map: dict[uuid.UUID, str] = {}

    if factory_ids:
        factory_result = await db.execute(select(Factory).where(Factory.id.in_(factory_ids)))
        factory_map = {item.id: item.name for item in factory_result.scalars().all()}
    if department_ids:
        department_result = await db.execute(select(Department).where(Department.id.in_(department_ids)))
        department_map = {item.id: item.name for item in department_result.scalars().all()}

    return [
        UserDetailRow(
            serial_no=item.serial_no,
            name=item.name,
            phone=item.phone,
            role=item.role.value,
            factory_name=factory_map.get(item.factory_id) if item.factory_id else None,
            department_name=department_map.get(item.department_id) if item.department_id else None,
            is_active=item.is_active,
            created_at=item.created_at.isoformat(),
        )
        for item in users
    ]

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
        d = _traffic_bucket_label(e.captured_at, granularity)
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


@router.get("/vehicle-details", response_model=list[VehicleDetailRow])
async def vehicle_detail_report(
    serial_no: str | None = Query(None),
    plate_number: str | None = Query(None),
    status: str | None = Query(None),
    company: str | None = Query(None),
    factory_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: str | list[uuid.UUID] = Depends(get_data_scope),
):
    query = apply_data_scope(select(Vehicle), Vehicle.factory_id, scope, factory_id)
    if serial_no:
        query = query.where(Vehicle.serial_no.ilike(f"%{serial_no}%"))
    if plate_number:
        query = query.where(Vehicle.plate_number.ilike(f"%{plate_number}%"))
    if status:
        query = query.where(Vehicle.status == status)
    if company:
        query = query.where(Vehicle.company.ilike(f"%{company}%"))

    result = await db.execute(query.order_by(Vehicle.created_at.desc()))
    return await _build_vehicle_detail_rows(list(result.scalars().all()))


@router.get("/user-details", response_model=list[UserDetailRow])
async def user_detail_report(
    serial_no: str | None = Query(None),
    name: str | None = Query(None),
    phone: str | None = Query(None),
    role: str | None = Query(None),
    department_id: uuid.UUID | None = Query(None),
    factory_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: str | list[uuid.UUID] = Depends(get_data_scope),
):
    query = apply_data_scope(select(User), User.factory_id, scope, factory_id)
    if user.role == UserRole.factory_manager:
        query = query.where(User.factory_id == user.factory_id)
    elif user.role == UserRole.operator:
        query = query.where(User.factory_id == user.factory_id)
        if user.department_id is not None:
            query = query.where(User.department_id == user.department_id)

    if serial_no:
        query = query.where(User.serial_no.ilike(f"%{serial_no}%"))
    if name:
        query = query.where(User.name.ilike(f"%{name}%"))
    if phone:
        query = query.where(User.phone.ilike(f"%{phone}%"))
    if role:
        query = query.where(User.role == role)
    if department_id is not None:
        query = query.where(User.department_id == department_id)

    result = await db.execute(query.order_by(User.created_at.desc()))
    return await _build_user_detail_rows(db, list(result.scalars().all()))

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


@router.get("/access-details", response_model=list[AccessDetailRow])
async def access_detail_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    serial_no: str | None = Query(None),
    plate_number: str | None = Query(None),
    direction: Direction | None = Query(None),
    checkpoint_id: uuid.UUID | None = Query(None),
    department_id: uuid.UUID | None = Query(None),
    entered_by_user_id: uuid.UUID | None = Query(None),
    business_type: str | None = Query(None),
    document_no: str | None = Query(None),
    source: str | None = Query(None),
    factory_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: str | list[uuid.UUID] = Depends(get_data_scope),
):
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    query = apply_data_scope(
        select(CheckpointEvent).where(
            CheckpointEvent.event_time >= start_dt,
            CheckpointEvent.event_time <= end_dt,
        ),
        CheckpointEvent.factory_id,
        scope,
        factory_id,
    )
    query = _apply_checkpoint_event_scope(query, user)

    if serial_no:
        query = query.where(CheckpointEvent.serial_no.ilike(f"%{serial_no}%"))
    if plate_number:
        query = query.where(CheckpointEvent.plate_number.ilike(f"%{plate_number}%"))
    if direction is not None:
        query = query.where(CheckpointEvent.direction == direction)
    if checkpoint_id is not None:
        query = query.where(CheckpointEvent.checkpoint_id == checkpoint_id)
    if department_id is not None:
        query = query.where(CheckpointEvent.department_id == department_id)
    if entered_by_user_id is not None:
        query = query.where(CheckpointEvent.entered_by_user_id == entered_by_user_id)
    if business_type:
        query = query.where(CheckpointEvent.business_type == CheckpointEventBusinessType(business_type))
    if document_no:
        query = query.where(CheckpointEvent.document_no.ilike(f"%{document_no}%"))
    if source:
        query = query.where(CheckpointEvent.source == CheckpointEventSource(source))

    result = await db.execute(query.order_by(CheckpointEvent.event_time.desc(), CheckpointEvent.created_at.desc()))
    return await _build_access_detail_rows(db, list(result.scalars().all()))


@router.get("/access-details/export")
async def export_access_detail_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    serial_no: str | None = Query(None),
    plate_number: str | None = Query(None),
    direction: Direction | None = Query(None),
    checkpoint_id: uuid.UUID | None = Query(None),
    department_id: uuid.UUID | None = Query(None),
    entered_by_user_id: uuid.UUID | None = Query(None),
    business_type: str | None = Query(None),
    document_no: str | None = Query(None),
    source: str | None = Query(None),
    factory_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: str | list[uuid.UUID] = Depends(get_data_scope),
):
    rows = await access_detail_report(
        start_date=start_date,
        end_date=end_date,
        serial_no=serial_no,
        plate_number=plate_number,
        direction=direction,
        checkpoint_id=checkpoint_id,
        department_id=department_id,
        entered_by_user_id=entered_by_user_id,
        business_type=business_type,
        document_no=document_no,
        source=source,
        factory_id=factory_id,
        db=db,
        user=user,
        scope=scope,
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "出入管理明细"
    ws.append(["流水号", "时间", "车牌", "方向", "节点", "部门", "业务类型", "单号", "来源", "操作用户", "备注"])
    for row in rows:
        ws.append([
            row.serial_no or "",
            row.event_time,
            row.plate_number,
            "入场" if row.direction == "entry" else "出场",
            row.checkpoint_name,
            row.department_name or "",
            row.business_type,
            row.document_no or "",
            row.source,
            row.entered_by_user_name or "",
            row.note or "",
        ])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=access_detail_{start_date}_{end_date}.xlsx"},
    )

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
