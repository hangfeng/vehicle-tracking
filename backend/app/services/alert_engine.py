from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.vehicle import Vehicle, VehicleStatus
from app.models.alert import Alert, AlertType, AlertSeverity, AlertStatus
from app.config import settings

async def check_long_stay(db: AsyncSession, factory_id) -> list[Alert]:
    threshold = datetime.utcnow() - timedelta(hours=settings.long_stay_hours)
    result = await db.execute(
        select(Vehicle).where(
            Vehicle.factory_id == factory_id,
            Vehicle.status == VehicleStatus.in_factory,
            Vehicle.last_seen_at <= threshold,
        )
    )
    vehicles = result.scalars().all()
    new_alerts = []
    for v in vehicles:
        existing = await db.execute(
            select(Alert).where(
                Alert.vehicle_id == v.id,
                Alert.type == AlertType.long_stay,
                Alert.status == AlertStatus.active,
            )
        )
        if existing.scalar_one_or_none():
            continue
        alert = Alert(
            factory_id=factory_id,
            vehicle_id=v.id,
            type=AlertType.long_stay,
            message=f"车辆 {v.plate_number} 已在厂超过 {settings.long_stay_hours} 小时",
            severity=AlertSeverity.warning,
        )
        db.add(alert)
        new_alerts.append(alert)
    if new_alerts:
        await db.commit()
    return new_alerts

async def create_pending_review_alert(db: AsyncSession, factory_id, plate_number: str) -> Alert:
    alert = Alert(
        factory_id=factory_id,
        type=AlertType.pending_review,
        message=f"车牌识别置信度不足，需人工审核：{plate_number}",
        severity=AlertSeverity.info,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert
