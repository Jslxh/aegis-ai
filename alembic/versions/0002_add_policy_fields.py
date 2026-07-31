"""add priority, version, enabled, tags to policies

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("policies", sa.Column("priority", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("policies", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("policies", sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("policies", sa.Column("tags", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("policies", "tags")
    op.drop_column("policies", "enabled")
    op.drop_column("policies", "version")
    op.drop_column("policies", "priority")
