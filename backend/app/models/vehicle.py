import uuid
import enum
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class VehicleStatus(str, enum.Enum):
    in_factory = "in_factory"
    out = "out"
    unknown = "unknown"

class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    serial_no: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)
    factory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("factories.id"))
    plate_number: Mapped[str] = mapped_column(String(20), index=True)
    vehicle_type: Mapped[str] = mapped_column(String(50), default="truck")
    company: Mapped[str | None] = mapped_column(String(100))
    contact_name: Mapped[str | None] = mapped_column(String(50))
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[VehicleStatus] = mapped_column(SAEnum(VehicleStatus), default=VehicleStatus.unknown)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    note: Mapped[str | None] = mapped_column(Text)
    current_checkpoint_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("checkpoints.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
