import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.path_template import StepDirection

class PathTemplateStepCreate(BaseModel):
    checkpoint_id: uuid.UUID
    step_order: int
    direction: StepDirection

class PathTemplateStepOut(BaseModel):
    id: uuid.UUID
    checkpoint_id: uuid.UUID
    step_order: int
    direction: StepDirection

    model_config = {"from_attributes": True}

class PathTemplateCreate(BaseModel):
    name: str
    steps: list[PathTemplateStepCreate]
    factory_id: uuid.UUID | None = None  # group_admin 指定目标厂区

class PathTemplateUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    steps: list[PathTemplateStepCreate] | None = None

class PathTemplateOut(BaseModel):
    id: uuid.UUID
    factory_id: uuid.UUID
    name: str
    is_active: bool
    created_at: datetime
    steps: list[PathTemplateStepOut] = []

    model_config = {"from_attributes": True}
