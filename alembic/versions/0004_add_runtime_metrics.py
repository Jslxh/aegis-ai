"""add runtime_metrics table

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "runtime_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("tool", sa.String(100), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("decision", sa.String(50), nullable=False),
        sa.Column("matched_rule", sa.String(255), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("execution_time_ms", sa.Float(), nullable=False),
        sa.Column("tool_latency_ms", sa.Float(), nullable=True),
        sa.Column("execution_status", sa.String(50), nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("request_data", sa.JSON(), nullable=True),
        sa.Column("tool_output", sa.JSON(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_runtime_metrics_timestamp"),
        "runtime_metrics",
        ["timestamp"],
    )
    op.create_index(
        op.f("ix_runtime_metrics_decision"),
        "runtime_metrics",
        ["decision"],
    )


def downgrade() -> None:
    op.drop_table("runtime_metrics")
