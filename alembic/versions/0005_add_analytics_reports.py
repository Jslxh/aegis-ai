"""add analytics_reports table

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analytics_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_type", sa.String(20), nullable=False),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_type", "period", name="uq_analytics_reports_type_period"),
    )
    op.create_index(
        op.f("ix_analytics_reports_report_type"),
        "analytics_reports",
        ["report_type"],
    )


def downgrade() -> None:
    op.drop_table("analytics_reports")
