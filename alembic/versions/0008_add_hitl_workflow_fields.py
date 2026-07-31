"""extend hitl_requests with full approval workflow fields

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-31

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("hitl_requests", sa.Column("reviewer", sa.String(length=255), nullable=True))
    op.add_column("hitl_requests", sa.Column("comments", sa.Text(), nullable=True))
    op.add_column("hitl_requests", sa.Column("expires_at", sa.DateTime(), nullable=True))
    op.add_column("hitl_requests", sa.Column("approved_at", sa.DateTime(), nullable=True))
    op.add_column("hitl_requests", sa.Column("rejected_at", sa.DateTime(), nullable=True))
    op.create_index("ix_hitl_requests_status", "hitl_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_hitl_requests_status", table_name="hitl_requests")
    op.drop_column("hitl_requests", "rejected_at")
    op.drop_column("hitl_requests", "approved_at")
    op.drop_column("hitl_requests", "expires_at")
    op.drop_column("hitl_requests", "comments")
    op.drop_column("hitl_requests", "reviewer")
