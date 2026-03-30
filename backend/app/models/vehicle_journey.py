import uuid
import enum
from datetime import datetime
from sqlalchemy import Text, Boolean, DateTime, ForeignKey, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class JourneyStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    deviated = "deviated"

class JourneyDirection(str, enum.Enum):
    entry = "entry"
    exit = "exit"

class VehicleJourney(Base):
    __tablename__ = "vehicle_journeys"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id"))
    factory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("factories.id"))
    template_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("path_templates.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[JourneyStatus] = mapped_column(SAEnum(JourneyStatus), default=JourneyStatus.active)

class JourneyEvent(Base):
    __tablename__ = "journey_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    journey_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicle_journeys.id"))
    gate_event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("gate_events.id"), nullable=True)
    checkpoint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("checkpoints.id"))
    direction: Mapped[JourneyDirection] = mapped_column(SAEnum(JourneyDirection))
    occurred_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    is_deviation: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
