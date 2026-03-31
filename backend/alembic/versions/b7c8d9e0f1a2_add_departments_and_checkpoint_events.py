"""add departments and checkpoint events

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-03-31 13:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    direction_enum = postgresql.ENUM("entry", "exit", name="direction", create_type=False)
    op.create_table(
        "departments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("factory_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["factory_id"], ["factories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column("users", sa.Column("department_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("users_department_id_fkey", "users", "departments", ["department_id"], ["id"])

    op.add_column("checkpoints", sa.Column("department_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "checkpoints_department_id_fkey",
        "checkpoints",
        "departments",
        ["department_id"],
        ["id"],
    )

    op.create_table(
        "checkpoint_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("factory_id", sa.Uuid(), nullable=False),
        sa.Column("checkpoint_id", sa.Uuid(), nullable=False),
        sa.Column("department_id", sa.Uuid(), nullable=True),
        sa.Column("vehicle_id", sa.Uuid(), nullable=True),
        sa.Column("plate_number", sa.String(length=20), nullable=False),
        sa.Column("direction", direction_enum, nullable=False),
        sa.Column("event_time", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("source", sa.Enum("manual", "ai", "import", name="checkpointeventsource"), nullable=False),
        sa.Column("entered_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("gate_event_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["factory_id"], ["factories.id"]),
        sa.ForeignKeyConstraint(["checkpoint_id"], ["checkpoints.id"]),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.ForeignKeyConstraint(["entered_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["gate_event_id"], ["gate_events.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_checkpoint_events_plate_number", "checkpoint_events", ["plate_number"])


def downgrade() -> None:
    op.drop_index("ix_checkpoint_events_plate_number", table_name="checkpoint_events")
    op.drop_table("checkpoint_events")
    op.drop_constraint("checkpoints_department_id_fkey", "checkpoints", type_="foreignkey")
    op.drop_column("checkpoints", "department_id")
    op.drop_constraint("users_department_id_fkey", "users", type_="foreignkey")
    op.drop_column("users", "department_id")
    op.drop_table("departments")
