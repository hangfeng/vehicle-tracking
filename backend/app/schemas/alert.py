import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.alert import AlertType, AlertSeverity, AlertStatus

class AlertOut(BaseModel):
    id: uuid.UUID
    factory_id: uuid.UUID
    vehicle_id: uuid.UUID | None
    type: AlertType
    message: str
    severity: AlertSeverity
    status: AlertStatus
    created_at: datetime
    resolved_at: datetime | None
    note: str | None

    model_config = {"from_attributes": True}

class ResolveRequest(BaseModel):
    note: str | None = None
