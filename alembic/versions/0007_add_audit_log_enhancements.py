"""add enterprise audit log enhancements (trace IDs, checksums, immutability)

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-31

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # audit_logs: trace + integrity columns
    op.add_column("audit_logs", sa.Column("event_type", sa.String(50), nullable=True))
    op.add_column("audit_logs", sa.Column("status", sa.String(50), nullable=True))
    op.add_column("audit_logs", sa.Column("risk_level", sa.String(20), nullable=True))
    op.add_column("audit_logs", sa.Column("correlation_id", sa.String(100), nullable=True))
    op.add_column("audit_logs", sa.Column("request_id", sa.String(100), nullable=True))
    op.add_column("audit_logs", sa.Column("execution_id", sa.String(100), nullable=True))
    op.add_column("audit_logs", sa.Column("source", sa.String(50), nullable=True))
    op.add_column("audit_logs", sa.Column("actor", sa.String(100), nullable=True))
    op.add_column("audit_logs", sa.Column("client_ip", sa.String(45), nullable=True))
    op.add_column("audit_logs", sa.Column("user_agent", sa.String(255), nullable=True))
    op.add_column("audit_logs", sa.Column("checksum", sa.String(64), nullable=True))
    op.add_column("audit_logs", sa.Column("prev_checksum", sa.String(64), nullable=True))

    op.create_index("ix_audit_logs_correlation_id", "audit_logs", ["correlation_id"])
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])
    op.create_index("ix_audit_logs_execution_id", "audit_logs", ["execution_id"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])

    # execution_history: trace columns
    op.add_column("execution_history", sa.Column("correlation_id", sa.String(100), nullable=True))
    op.add_column("execution_history", sa.Column("request_id", sa.String(100), nullable=True))
    op.add_column("execution_history", sa.Column("execution_id", sa.String(100), nullable=True))
    op.create_index("ix_execution_history_correlation_id", "execution_history", ["correlation_id"])
    op.create_index("ix_execution_history_request_id", "execution_history", ["request_id"])
    op.create_index("ix_execution_history_execution_id", "execution_history", ["execution_id"])

    # runtime_metrics: trace columns
    op.add_column("runtime_metrics", sa.Column("correlation_id", sa.String(100), nullable=True))
    op.add_column("runtime_metrics", sa.Column("request_id", sa.String(100), nullable=True))
    op.add_column("runtime_metrics", sa.Column("execution_id", sa.String(100), nullable=True))
    op.create_index("ix_runtime_metrics_correlation_id", "runtime_metrics", ["correlation_id"])
    op.create_index("ix_runtime_metrics_request_id", "runtime_metrics", ["request_id"])
    op.create_index("ix_runtime_metrics_execution_id", "runtime_metrics", ["execution_id"])

    # Immutability trigger: prevent UPDATE / DELETE on audit_logs
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_audit_log_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs are immutable: UPDATE and DELETE are not permitted';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_audit_logs_immutable
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_log_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_immutable ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_log_mutation()")

    op.drop_index("ix_runtime_metrics_execution_id", table_name="runtime_metrics")
    op.drop_index("ix_runtime_metrics_request_id", table_name="runtime_metrics")
    op.drop_index("ix_runtime_metrics_correlation_id", table_name="runtime_metrics")
    op.drop_column("runtime_metrics", "execution_id")
    op.drop_column("runtime_metrics", "request_id")
    op.drop_column("runtime_metrics", "correlation_id")

    op.drop_index("ix_execution_history_execution_id", table_name="execution_history")
    op.drop_index("ix_execution_history_request_id", table_name="execution_history")
    op.drop_index("ix_execution_history_correlation_id", table_name="execution_history")
    op.drop_column("execution_history", "execution_id")
    op.drop_column("execution_history", "request_id")
    op.drop_column("execution_history", "correlation_id")

    op.drop_index("ix_audit_logs_timestamp", table_name="audit_logs")
    op.drop_index("ix_audit_logs_execution_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_request_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_correlation_id", table_name="audit_logs")
    op.drop_column("audit_logs", "prev_checksum")
    op.drop_column("audit_logs", "checksum")
    op.drop_column("audit_logs", "user_agent")
    op.drop_column("audit_logs", "client_ip")
    op.drop_column("audit_logs", "actor")
    op.drop_column("audit_logs", "source")
    op.drop_column("audit_logs", "execution_id")
    op.drop_column("audit_logs", "request_id")
    op.drop_column("audit_logs", "correlation_id")
    op.drop_column("audit_logs", "risk_level")
    op.drop_column("audit_logs", "status")
    op.drop_column("audit_logs", "event_type")
