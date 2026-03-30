import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class StepDirection(str, enum.Enum):
    entry = "entry"
    exit = "exit"
    any = "any"

class PathTemplate(Base):
    __tablename__ = "path_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    factory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("factories.id"))
    name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    steps: Mapped[list["PathTemplateStep"]] = relationship("PathTemplateStep", lazy="select")

class PathTemplateStep(Base):
    __tablename__ = "path_template_steps"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("path_templates.id"))
    checkpoint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("checkpoints.id"))
    step_order: Mapped[int] = mapped_column(Integer)
    direction: Mapped[StepDirection] = mapped_column(SAEnum(StepDirection))
