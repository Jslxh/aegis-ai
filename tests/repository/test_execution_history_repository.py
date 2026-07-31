"""Repository tests for ExecutionHistoryRepository."""

import pytest

from app.database.repositories.execution_history_repository import ExecutionHistoryRepository


@pytest.mark.repo
class TestExecutionHistoryRepository:
    def test_create_record(self, db_session):
        repo = ExecutionHistoryRepository(db_session)
        record = repo.create_record(
            {"tool": "database", "action": "delete", "record_count": 5},
            {"decision": "block", "matched_rule": "r1", "reason": "too big"},
            execution_status="blocked",
            tool_output={"detail": "no"},
            correlation_id="corr_1",
            request_id="req_1",
            execution_id="exec_1",
        )
        db_session.commit()
        assert record.tool == "database"
        assert record.decision == "block"
        assert record.matched_rule == "r1"
        assert record.tool_output == {"detail": "no"}

    def test_create_uses_empty_defaults(self, db_session):
        repo = ExecutionHistoryRepository(db_session)
        record = repo.create_record({"tool": "email"}, {"decision": "allow"}, execution_status="executed")
        db_session.commit()
        assert record.correlation_id is None
        assert record.tool_output is None

    def test_list_recent(self, db_session):
        from datetime import datetime, timedelta

        repo = ExecutionHistoryRepository(db_session)
        now = datetime.utcnow()
        r1 = repo.create_record({"tool": "a"}, {"decision": "allow"}, execution_status="executed")
        r1.created_at = now - timedelta(seconds=10)
        r2 = repo.create_record({"tool": "b"}, {"decision": "block"}, execution_status="blocked")
        db_session.commit()
        recent = repo.list_recent()
        assert recent[0].id == r2.id

    def test_list_recent_limit(self, db_session):
        repo = ExecutionHistoryRepository(db_session)
        for i in range(5):
            repo.create_record({"tool": f"t{i}"}, {"decision": "allow"}, execution_status="executed")
        db_session.commit()
        assert len(repo.list_recent(limit=3)) == 3
