import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.checkpoint_event import CheckpointEventBusinessType, CheckpointEventSource
from app.models.gate_event import Direction


class CheckpointEventCreate(BaseModel):
    checkpoint_id: uuid.UUID
    plate_number: str
    direction: Direction
    business_type: CheckpointEventBusinessType = CheckpointEventBusinessType.other
    document_no: str | None = None
    event_time: datetime | None = None
    note: str | None = None


class CheckpointEventOut(BaseModel):
    id: uuid.UUID
    serial_no: str | None
    factory_id: uuid.UUID
    checkpoint_id: uuid.UUID
    department_id: uuid.UUID | None
    vehicle_id: uuid.UUID | None
    plate_number: str
    direction: Direction
    event_time: datetime
    source: CheckpointEventSource
    business_type: CheckpointEventBusinessType
    document_no: str | None
    entered_by_user_id: uuid.UUID | None
    entered_by_user_name: str | None = None
    note: str | None
    gate_event_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
