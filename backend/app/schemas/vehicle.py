import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.vehicle import VehicleStatus

class VehicleCreate(BaseModel):
    plate_number: str
    vehicle_type: str = "truck"
    company: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    note: str | None = None

class VehicleUpdate(BaseModel):
    vehicle_type: str | None = None
    company: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    note: str | None = None

class VehicleOut(BaseModel):
    id: uuid.UUID
    factory_id: uuid.UUID
    plate_number: str
    vehicle_type: str
    company: str | None
    contact_name: str | None
    contact_phone: str | None
    status: VehicleStatus
    last_seen_at: datetime | None
    note: str | None

    model_config = {"from_attributes": True}
