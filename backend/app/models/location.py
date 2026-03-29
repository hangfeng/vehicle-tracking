import uuid
import enum
from sqlalchemy import String, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class LocationType(str, enum.Enum):
    gate = "gate"
    checkpoint = "checkpoint"

class Location(Base):
    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    factory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("factories.id"))
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[LocationType] = mapped_column(SAEnum(LocationType), default=LocationType.gate)
    camera_ip: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
