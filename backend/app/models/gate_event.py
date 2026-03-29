import uuid
import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Float, Boolean, ForeignKey, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class ReviewStatus(str, enum.Enum):
    auto_confirmed = "auto_confirmed"
    pending_review = "pending_review"
    manually_confirmed = "manually_confirmed"
    rejected = "rejected"

class Direction(str, enum.Enum):
    entry = "entry"
    exit = "exit"

class GateEvent(Base):
    __tablename__ = "gate_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    factory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("factories.id"))
    gate_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    plate_number: Mapped[str] = mapped_column(String(20), index=True)
    direction: Mapped[Direction] = mapped_column(SAEnum(Direction))
    captured_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    image_url: Mapped[str | None] = mapped_column(String(500))
    confidence_score: Mapped[float | None] = mapped_column(Float)
    review_status: Mapped[ReviewStatus] = mapped_column(SAEnum(ReviewStatus), default=ReviewStatus.pending_review)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False)
