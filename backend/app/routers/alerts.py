import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models.alert import Alert, AlertStatus
from app.models.user import User
from app.schemas.alert import AlertOut, ResolveRequest
from app.deps import get_current_user

router = APIRouter(prefix="/alerts", tags=["alerts"])

@router.get("", response_model=list[AlertOut])
async def list_alerts(
    status: AlertStatus | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Alert).where(Alert.factory_id == user.factory_id)
    if status:
        q = q.where(Alert.status == status)
    q = q.order_by(desc(Alert.created_at)).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()

@router.patch("/{alert_id}/resolve", response_model=AlertOut)
async def resolve_alert(
    alert_id: uuid.UUID,
    body: ResolveRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.factory_id == user.factory_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = AlertStatus.resolved
    alert.resolved_by = user.id
    alert.resolved_at = datetime.utcnow()
    alert.note = body.note
    await db.commit()
    await db.refresh(alert)
    return alert
