import uuid
from datetime import datetime

from pydantic import BaseModel


class DepartmentCreate(BaseModel):
    name: str
    factory_id: uuid.UUID | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None


class DepartmentOut(BaseModel):
    id: uuid.UUID
    factory_id: uuid.UUID
    name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
