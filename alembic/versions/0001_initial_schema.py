"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "policies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rule_id", sa.String(255), nullable=False),
        sa.Column("tool", sa.String(100), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=False),
        sa.Column("combinator", sa.String(10), nullable=False, server_default="AND"),
        sa.Column("decision", sa.String(50), nullable=False),
        sa.Column("message", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_id"),
    )
    op.create_index(op.f("ix_policies_rule_id"), "policies", ["rule_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("tool", sa.String(100), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("request_data", sa.JSON(), nullable=False),
        sa.Column("decision", sa.String(50), nullable=False),
        sa.Column("matched_rule", sa.String(255), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "hitl_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("request_id", sa.String(255), nullable=False),
        sa.Column("tool", sa.String(100), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("request_data", sa.JSON(), nullable=False),
        sa.Column("policy_decision", sa.String(50), nullable=False),
        sa.Column("policy_reason", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("approval_reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index(op.f("ix_hitl_requests_request_id"), "hitl_requests", ["request_id"])

    op.create_table(
        "simulation_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("total_scenarios", sa.Integer(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("results", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "execution_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tool", sa.String(100), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("request_data", sa.JSON(), nullable=False),
        sa.Column("decision", sa.String(50), nullable=False),
        sa.Column("matched_rule", sa.String(255), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("execution_status", sa.String(50), nullable=False),
        sa.Column("tool_output", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("execution_history")
    op.drop_table("simulation_runs")
    op.drop_table("hitl_requests")
    op.drop_table("audit_logs")
    op.drop_table("policies")
