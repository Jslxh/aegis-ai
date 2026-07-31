"""API tests for monitoring endpoints: metrics, dashboard, activity, violations."""

import pytest

from app.database.repositories.runtime_metric_repository import RuntimeMetricRepository
from app.api.monitoring_routes import _parse_time_range, _risk_level


def _seed_metrics(session_factory, n=3):
    session = session_factory()
    try:
        repo = RuntimeMetricRepository(session)
        for i in range(n):
            repo.create_metric(
                tool="database",
                action="delete",
                decision="block" if i % 2 else "allow",
                execution_status="executed",
                risk_level="medium",
                execution_time_ms=50.0,
                tool_latency_ms=10.0,
                matched_rule="r1" if i % 2 else None,
            )
        session.commit()
    finally:
        session.close()


@pytest.mark.api
class TestParseTimeRange:
    def test_known_ranges(self):
        assert _parse_time_range("1h") is not None
        assert _parse_time_range("24h") is not None
        assert _parse_time_range("7d") is not None
        assert _parse_time_range("30d") is not None
        assert _parse_time_range("all") is None

    def test_unknown_falls_back_to_24h(self):
        since = _parse_time_range("bogus")
        assert since is not None


@pytest.mark.api
class TestRiskLevelHelper:
    def test_mapping(self):
        assert _risk_level("block", "executed") == "critical"
        assert _risk_level("allow", "failed") == "high"
        assert _risk_level("require_hitl", "executed") == "high"
        assert _risk_level("log_and_allow", "executed") == "medium"
        assert _risk_level("allow", "executed") == "low"


@pytest.mark.api
class TestMonitoringMetrics:
    def test_metrics_summary(self, client, auth_headers_factory, session_factory):
        _seed_metrics(session_factory)
        res = client.get("/monitoring/metrics", headers=auth_headers_factory("viewer"))
        assert res.status_code == 200
        body = res.json()
        assert body["total_requests"] == 3
        assert body["blocked_count"] == 1
        assert body["allowed_count"] == 2

    def test_metrics_time_range(self, client, auth_headers_factory, session_factory):
        _seed_metrics(session_factory)
        assert client.get("/monitoring/metrics?time_range=all", headers=auth_headers_factory("viewer")).json()["total_requests"] == 3

    def test_metrics_requires_auth(self, client):
        assert client.get("/monitoring/metrics").status_code == 401

    def test_metrics_timeline_needs_postgres(self, client, auth_headers_factory, session_factory):
        _seed_metrics(session_factory)
        res = client.get("/monitoring/metrics/timeline", headers=auth_headers_factory("viewer"))
        assert res.status_code == 500


@pytest.mark.api
class TestDashboard:
    def test_dashboard(self, client, auth_headers_factory, session_factory):
        _seed_metrics(session_factory)
        res = client.get("/monitoring/dashboard", headers=auth_headers_factory("viewer"))
        assert res.status_code == 200
        body = res.json()
        assert body["total_requests"] == 3
        assert body["blocked_count"] == 1
        assert body["success_rate"] == 100.0
        assert body["active_rules_count"] == 0
        assert body["top_risk_level"] == "medium"
        assert len(body["recent_activity"]) == 3

    def test_dashboard_empty(self, client, auth_headers_factory):
        res = client.get("/monitoring/dashboard", headers=auth_headers_factory("viewer"))
        assert res.status_code == 200
        body = res.json()
        assert body["total_requests"] == 0
        assert body["top_risk_level"] == "low"


@pytest.mark.api
class TestActivityAndViolations:
    def test_activity(self, client, auth_headers_factory, session_factory):
        _seed_metrics(session_factory)
        res = client.get("/monitoring/activity", headers=auth_headers_factory("viewer"))
        assert res.status_code == 200
        items = res.json()
        assert len(items) == 3
        assert items[0]["risk_level"] == "medium"

    def test_activity_limit(self, client, auth_headers_factory, session_factory):
        _seed_metrics(session_factory, n=5)
        res = client.get("/monitoring/activity?limit=2", headers=auth_headers_factory("viewer"))
        assert len(res.json()) == 2

    def test_top_violations(self, client, auth_headers_factory, session_factory):
        _seed_metrics(session_factory, n=5)
        res = client.get("/monitoring/violations/top", headers=auth_headers_factory("viewer"))
        assert res.status_code == 200
        items = res.json()
        assert len(items) == 1
        assert items[0]["matched_rule"] == "r1"

    def test_raw_metrics_requires_auditor(self, client, auth_headers_factory, session_factory):
        _seed_metrics(session_factory)
        assert client.get("/monitoring/metrics/raw", headers=auth_headers_factory("viewer")).status_code == 403
        res = client.get("/monitoring/metrics/raw?decision=block", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        assert len(res.json()) == 1
