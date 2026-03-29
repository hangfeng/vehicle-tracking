import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.gate_event import Direction, ReviewStatus

class GateEventCreate(BaseModel):
    factory_id: uuid.UUID
    gate_id: uuid.UUID | None = None
    plate_number: str
    direction: Direction
    image_url: str | None = None
    confidence_score: float | None = None

class ReviewRequest(BaseModel):
    plate_number: str
    action: str  # "confirm" or "reject"

class GateEventOut(BaseModel):
    id: uuid.UUID
    factory_id: uuid.UUID
    plate_number: str
    direction: Direction
    captured_at: datetime
    image_url: str | None
    confidence_score: float | None
    review_status: ReviewStatus
    is_manual: bool

    model_config = {"from_attributes": True}
