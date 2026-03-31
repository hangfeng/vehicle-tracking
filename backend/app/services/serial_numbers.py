from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def build_serial_prefix(module_prefix: str, at: datetime) -> str:
    return f"{module_prefix}{at.strftime('%Y%m%d%H%M%S')}"


async def generate_serial_no(
    db: AsyncSession,
    *,
    model,
    serial_column,
    module_prefix: str,
    at: datetime | None = None,
) -> str:
    timestamp = at or datetime.utcnow()
    serial_prefix = build_serial_prefix(module_prefix, timestamp)
    result = await db.execute(
        select(func.count()).select_from(model).where(serial_column.like(f"{serial_prefix}%"))
    )
    sequence = (result.scalar() or 0) + 1
    return f"{serial_prefix}{sequence:03d}"
