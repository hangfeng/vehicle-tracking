"""add serial numbers

Revision ID: e5f6a7b8c9d0
Revises: c1d2e3f4a5b6
Create Date: 2026-03-31 14:30:00.000000
"""

from collections import defaultdict
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def _serial_value(prefix: str, value: datetime | None, counters: dict[str, int]) -> str:
    timestamp = value or datetime.utcnow()
    base = f"{prefix}{timestamp.strftime('%Y%m%d%H%M%S')}"
    counters[base] += 1
    return f"{base}{counters[base]:03d}"


def _backfill_serials(bind, table_name: str, prefix: str, time_column_name: str) -> None:
    metadata = sa.MetaData()
    table = sa.Table(
        table_name,
        metadata,
        sa.Column("id", sa.Uuid()),
        sa.Column("serial_no", sa.String()),
        sa.Column(time_column_name, sa.DateTime()),
    )
    rows = bind.execute(
        sa.select(table.c.id, getattr(table.c, time_column_name))
        .where(table.c.serial_no.is_(None))
        .order_by(getattr(table.c, time_column_name), table.c.id)
    ).fetchall()

    counters: dict[str, int] = defaultdict(int)
    for row in rows:
        bind.execute(
            table.update()
            .where(table.c.id == row.id)
            .values(serial_no=_serial_value(prefix, getattr(row, time_column_name), counters))
        )


def upgrade() -> None:
    op.add_column("users", sa.Column("serial_no", sa.String(length=32), nullable=True))
    op.add_column("vehicles", sa.Column("serial_no", sa.String(length=32), nullable=True))
    op.add_column("checkpoint_events", sa.Column("serial_no", sa.String(length=32), nullable=True))

    bind = op.get_bind()
    _backfill_serials(bind, "users", "USR", "created_at")
    _backfill_serials(bind, "vehicles", "VEH", "created_at")
    _backfill_serials(bind, "checkpoint_events", "IO", "event_time")

    op.create_index(op.f("ix_users_serial_no"), "users", ["serial_no"], unique=True)
    op.create_index(op.f("ix_vehicles_serial_no"), "vehicles", ["serial_no"], unique=True)
    op.create_index(op.f("ix_checkpoint_events_serial_no"), "checkpoint_events", ["serial_no"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_checkpoint_events_serial_no"), table_name="checkpoint_events")
    op.drop_index(op.f("ix_vehicles_serial_no"), table_name="vehicles")
    op.drop_index(op.f("ix_users_serial_no"), table_name="users")
    op.drop_column("checkpoint_events", "serial_no")
    op.drop_column("vehicles", "serial_no")
    op.drop_column("users", "serial_no")
