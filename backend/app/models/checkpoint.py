import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum as SAEnum, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class IdentificationMethod(str, enum.Enum):
    camera = "camera"
    manual = "manual"

class CheckPoint(Base):
    __tablename__ = "checkpoints"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    factory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("factories.id"))
    department_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(100))
    identification_method: Mapped[IdentificationMethod] = mapped_column(SAEnum(IdentificationMethod))
    is_gate: Mapped[bool] = mapped_column(Boolean, default=False)
    camera_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
