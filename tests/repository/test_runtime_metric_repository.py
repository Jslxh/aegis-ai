"""Repository tests for RuntimeMetricRepository."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import OperationalError

from app.database.repositories.runtime_metric_repository import RuntimeMetricRepository


def _create(repo, *, decision="allow", status="executed", rule=None, tool="database", action="delete"):
    return repo.create_metric(
        tool=tool,
        action=action,
        decision=decision,
        execution_status=status,
        risk_level="medium",
        execution_time_ms=100.0,
        tool_latency_ms=20.0,
        matched_rule=rule,
        correlation_id=f"corr_{rule or decision}_{id(rule)}",
    )


@pytest.mark.repo
class TestRuntimeMetricRepository:
    def test_create_metric(self, db_session):
        repo = RuntimeMetricRepository(db_session)
        m = _create(repo)
        db_session.commit()
        assert m.tool == "database"
        assert m.execution_time_ms == 100.0
        assert m.risk_level == "medium"

    def test_summary_counts_decisions(self, db_session):
        repo = RuntimeMetricRepository(db_session)
        _create(repo, decision="allow")
        _create(repo, decision="block", rule="r1")
        _create(repo, decision="block", rule="r2")
        _create(repo, decision="require_hitl")
        _create(repo, decision="log_and_allow")
        _create(repo, decision="allow", status="failed")
        db_session.commit()

        s = repo.summary()
        assert s["total_requests"] == 6
        assert s["blocked_count"] == 2
        assert s["allowed_count"] == 2
        assert s["hitl_count"] == 1
        assert s["log_and_allow_count"] == 1
        assert s["success_count"] == 5
        assert s["failure_count"] == 1
        assert s["avg_execution_time_ms"] == 100.0

    def test_summary_empty(self, db_session):
        repo = RuntimeMetricRepository(db_session)
        s = repo.summary()
        assert s["total_requests"] == 0
        assert s["avg_execution_time_ms"] == 0.0
        assert s["avg_tool_latency_ms"] is None

    def test_summary_since_filter(self, db_session):
        repo = RuntimeMetricRepository(db_session)
        _create(repo, decision="block", rule="old")
        db_session.commit()
        since = datetime.utcnow() - timedelta(minutes=1)
        s = repo.summary(since=since)
        assert s["total_requests"] == 1

        future = datetime.utcnow() + timedelta(hours=1)
        s2 = repo.summary(since=future)
        assert s2["total_requests"] == 0

    def test_recent_activity_orders_desc(self, db_session):
        repo = RuntimeMetricRepository(db_session)
        now = datetime.utcnow()
        m1 = _create(repo, decision="allow")
        m1.timestamp = now - timedelta(seconds=30)
        _create(repo, decision="block", rule="r1")
        db_session.commit()

        recent = repo.recent_activity(limit=10)
        assert len(recent) == 2
        assert recent[0].id > recent[1].id

    def test_top_violations(self, db_session):
        repo = RuntimeMetricRepository(db_session)
        for _ in range(3):
            _create(repo, decision="block", rule="r_big")
        _create(repo, decision="block", rule="r_other")
        _create(repo, decision="allow")
        db_session.commit()

        violations = repo.top_violations()
        assert len(violations) == 2
        assert violations[0]["matched_rule"] == "r_big"
        assert violations[0]["count"] == 3
        assert violations[0]["tool"] == "database"

    def test_top_violations_since(self, db_session):
        repo = RuntimeMetricRepository(db_session)
        _create(repo, decision="block", rule="r1")
        db_session.commit()
        assert repo.top_violations(since=datetime.utcnow() - timedelta(minutes=1))[0]["count"] == 1

    def test_timeline_requires_postgres(self, db_session):
        """date_trunc is PostgreSQL-only; SQLite must raise."""
        repo = RuntimeMetricRepository(db_session)
        _create(repo, decision="block", rule="r1")
        db_session.commit()
        with pytest.raises(OperationalError):
            repo.timeline(since=datetime.utcnow() - timedelta(hours=1))
