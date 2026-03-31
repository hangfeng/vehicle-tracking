import uuid
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.gate_event import Direction


class CheckpointEventSource(str, enum.Enum):
    manual = "manual"
    ai = "ai"
    import_ = "import"


class CheckpointEventBusinessType(str, enum.Enum):
    delivery = "delivery"
    shipment = "shipment"
    other = "other"


class CheckpointEvent(Base):
    __tablename__ = "checkpoint_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    serial_no: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)
    factory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("factories.id"))
    checkpoint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("checkpoints.id"))
    department_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    plate_number: Mapped[str] = mapped_column(String(20), index=True)
    direction: Mapped[Direction] = mapped_column(SAEnum(Direction))
    event_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    source: Mapped[CheckpointEventSource] = mapped_column(
        SAEnum(
            CheckpointEventSource,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            name="checkpointeventsource",
        ),
        default=CheckpointEventSource.manual,
    )
    business_type: Mapped[CheckpointEventBusinessType] = mapped_column(
        SAEnum(
            CheckpointEventBusinessType,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            name="checkpointeventbusinesstype",
        ),
        default=CheckpointEventBusinessType.other,
    )
    document_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    gate_event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("gate_events.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
