import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.user import UserRole

class UserCreate(BaseModel):
    phone: str
    name: str
    password: str
    role: UserRole
    factory_id: uuid.UUID | None = None

class UserUpdate(BaseModel):
    name: str | None = None
    role: UserRole | None = None
    factory_id: uuid.UUID | None = None
    is_active: bool | None = None

class UserOut(BaseModel):
    id: uuid.UUID
    phone: str
    name: str
    role: UserRole
    factory_id: uuid.UUID | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class BatchStatusRequest(BaseModel):
    ids: list[uuid.UUID]
    is_active: bool

class BatchStatusResponse(BaseModel):
    updated: int
