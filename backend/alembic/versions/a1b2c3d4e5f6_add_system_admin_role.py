"""add system_admin role

Revision ID: a1b2c3d4e5f6
Revises: de7744915ea6
Create Date: 2026-03-31 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'de7744915ea6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute(sa.text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'system_admin'"))

def downgrade() -> None:
    # PostgreSQL does not support removing enum values
    pass
