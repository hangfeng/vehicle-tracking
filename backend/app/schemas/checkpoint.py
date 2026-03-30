import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.checkpoint import IdentificationMethod

class CheckPointCreate(BaseModel):
    name: str
    identification_method: IdentificationMethod
    is_gate: bool = False
    camera_config: dict | None = None

class CheckPointUpdate(BaseModel):
    name: str | None = None
    identification_method: IdentificationMethod | None = None
    is_gate: bool | None = None
    camera_config: dict | None = None
    is_active: bool | None = None

class CheckPointOut(BaseModel):
    id: uuid.UUID
    factory_id: uuid.UUID
    name: str
    identification_method: IdentificationMethod
    is_gate: bool
    camera_config: dict | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
