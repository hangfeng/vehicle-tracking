import uuid
from datetime import datetime
from pydantic import BaseModel


class FactoryCreate(BaseModel):
    name: str
    address: str | None = None
    timezone: str = "Asia/Shanghai"


class FactoryUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    timezone: str | None = None
    is_active: bool | None = None


class FactoryOut(BaseModel):
    id: uuid.UUID
    name: str
    address: str | None
    timezone: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
