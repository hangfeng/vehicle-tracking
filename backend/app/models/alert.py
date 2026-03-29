import uuid
import enum
from datetime import datetime
from sqlalchemy import Text, DateTime, ForeignKey, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class AlertType(str, enum.Enum):
    long_stay = "long_stay"
    pending_review = "pending_review"

class AlertSeverity(str, enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"

class AlertStatus(str, enum.Enum):
    active = "active"
    resolved = "resolved"

class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    factory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("factories.id"))
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    type: Mapped[AlertType] = mapped_column(SAEnum(AlertType))
    message: Mapped[str] = mapped_column(Text)
    severity: Mapped[AlertSeverity] = mapped_column(SAEnum(AlertSeverity), default=AlertSeverity.warning)
    status: Mapped[AlertStatus] = mapped_column(SAEnum(AlertStatus), default=AlertStatus.active)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    note: Mapped[str | None] = mapped_column(Text)
