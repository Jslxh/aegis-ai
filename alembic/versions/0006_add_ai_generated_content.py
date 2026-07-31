"""add ai_generated_content table

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_generated_content",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("tool", sa.String(100), nullable=True),
        sa.Column("action", sa.String(100), nullable=True),
        sa.Column("decision", sa.String(50), nullable=True),
        sa.Column("matched_rule", sa.String(255), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("risk_analysis", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(20), nullable=True),
        sa.Column("recommendations", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ai_generated_content_source"),
        "ai_generated_content",
        ["source_type", "source_id"],
    )
    op.create_index(
        op.f("ix_ai_generated_content_type"),
        "ai_generated_content",
        ["content_type"],
    )


def downgrade() -> None:
    op.drop_table("ai_generated_content")
