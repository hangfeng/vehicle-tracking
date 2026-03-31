"""add business fields to checkpoint events

Revision ID: c1d2e3f4a5b6
Revises: b7c8d9e0f1a2
Create Date: 2026-03-31 13:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    business_type_enum = postgresql.ENUM(
        "delivery",
        "shipment",
        "other",
        name="checkpointeventbusinesstype",
    )
    business_type_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "checkpoint_events",
        sa.Column(
            "business_type",
            business_type_enum,
            nullable=False,
            server_default="other",
        ),
    )
    op.add_column("checkpoint_events", sa.Column("document_no", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("checkpoint_events", "document_no")
    op.drop_column("checkpoint_events", "business_type")
