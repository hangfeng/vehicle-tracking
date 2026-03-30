import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.vehicle_journey import JourneyStatus, JourneyDirection

class VehicleJourneyCreate(BaseModel):
    vehicle_id: uuid.UUID
    factory_id: uuid.UUID
    template_id: uuid.UUID | None = None

class JourneyEventCreate(BaseModel):
    journey_id: uuid.UUID
    checkpoint_id: uuid.UUID
    direction: JourneyDirection
    license_plate: str | None = None
    confidence: float | None = None
    image_url: str | None = None
    notes: str | None = None

class JourneyEventOut(BaseModel):
    id: uuid.UUID
    journey_id: uuid.UUID
    checkpoint_id: uuid.UUID
    direction: JourneyDirection
    occurred_at: datetime
    is_deviation: bool
    notes: str | None

    model_config = {"from_attributes": True}

class VehicleJourneyOut(BaseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    factory_id: uuid.UUID
    template_id: uuid.UUID | None
    started_at: datetime
    completed_at: datetime | None
    status: JourneyStatus

    model_config = {"from_attributes": True}
