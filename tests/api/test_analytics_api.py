"""API tests for analytics endpoints (SQLite-compatible subset + documented PG-only 500s)."""

import pytest

from app.database.repositories.runtime_metric_repository import RuntimeMetricRepository
from app.database.repositories.analytics_repository import AnalyticsRepository


def _seed_metrics(session_factory):
    session = session_factory()
    try:
        repo = RuntimeMetricRepository(session)
        repo.create_metric(
            tool="database", action="delete", decision="block", execution_status="executed",
            risk_level="critical", execution_time_ms=50.0, matched_rule="r1",
        )
        repo.create_metric(
            tool="database", action="delete", decision="allow", execution_status="executed",
            risk_level="low", execution_time_ms=25.0, matched_rule=None,
        )
        session.commit()
    finally:
        session.close()


@pytest.mark.api
class TestAnalyticsQueries:
    def test_policy_effectiveness(self, client, auth_headers_factory, session_factory):
        _seed_metrics(session_factory)
        res = client.get("/analytics/policy-effectiveness", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        body = res.json()
        assert body["total_rules"] == 1
        assert body["items"][0]["rule_id"] == "r1"
        assert body["items"][0]["blocked_count"] == 1

    def test_most_triggered_rules(self, client, auth_headers_factory, session_factory):
        _seed_metrics(session_factory)
        res = client.get("/analytics/most-triggered-rules", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        assert res.json()["items"][0]["rule_id"] == "r1"

    def test_most_dangerous_tools(self, client, auth_headers_factory, session_factory):
        _seed_metrics(session_factory)
        res = client.get("/analytics/most-dangerous-tools", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        items = res.json()["items"]
        assert items[0]["tool"] == "database"
        assert items[0]["block_rate_pct"] == 50.0

    def test_risk_distribution(self, client, auth_headers_factory, session_factory):
        _seed_metrics(session_factory)
        res = client.get("/analytics/risk-distribution", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 2

    def test_hitl_statistics(self, client, auth_headers_factory, session_factory):
        res = client.get("/analytics/hitl-statistics", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        body = res.json()
        assert body["total_requests"] == 0
        assert body["approval_rate_pct"] == 0.0

    def test_blocked_requests_needs_postgres(self, client, auth_headers_factory, session_factory):
        _seed_metrics(session_factory)
        assert client.get("/analytics/blocked-requests", headers=auth_headers_factory("auditor")).status_code == 500

    def test_avg_response_time_needs_postgres(self, client, auth_headers_factory, session_factory):
        _seed_metrics(session_factory)
        assert client.get("/analytics/avg-response-time", headers=auth_headers_factory("auditor")).status_code == 500

    def test_requires_auditor(self, client, auth_headers_factory):
        assert client.get("/analytics/policy-effectiveness", headers=auth_headers_factory("viewer")).status_code == 403


@pytest.mark.api
class TestAnalyticsReports:
    def test_generate_daily_needs_postgres(self, client, auth_headers_factory):
        res = client.post(
            "/analytics/reports/daily?date=2026-01-01", headers=auth_headers_factory("admin")
        )
        assert res.status_code == 500

    def test_generate_daily_invalid_date(self, client, auth_headers_factory):
        res = client.post(
            "/analytics/reports/daily?date=not-a-date", headers=auth_headers_factory("admin")
        )
        assert res.status_code == 400

    def test_generate_requires_admin(self, client, auth_headers_factory):
        assert (
            client.post("/analytics/reports/daily?date=2026-01-01", headers=auth_headers_factory("auditor")).status_code
            == 403
        )

    def test_list_reports(self, client, auth_headers_factory, session_factory):
        session = session_factory()
        try:
            repo = AnalyticsRepository(session)
            repo.upsert_report("daily", "2026-01-01", {"summary": {"total": 0}})
            session.commit()
        finally:
            session.close()

        res = client.get("/analytics/reports", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        assert len(res.json()) == 1

        filtered = client.get("/analytics/reports?report_type=monthly", headers=auth_headers_factory("auditor"))
        assert filtered.json() == []

    def test_get_report(self, client, auth_headers_factory, session_factory):
        session = session_factory()
        try:
            repo = AnalyticsRepository(session)
            repo.upsert_report("monthly", "2026-01", {"summary": {"total": 5}})
            session.commit()
        finally:
            session.close()

        res = client.get("/analytics/reports/monthly/2026-01", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        assert res.json()["period"] == "2026-01"

    def test_get_report_missing_404(self, client, auth_headers_factory):
        res = client.get("/analytics/reports/monthly/1999-01", headers=auth_headers_factory("auditor"))
        assert res.status_code == 404


@pytest.mark.api
class TestAnalyticsErrorPaths:
    """SQLAlchemyError branches in analytics routes return 500."""

    @pytest.fixture(autouse=True)
    def _boom(self, monkeypatch):
        from sqlalchemy.exc import SQLAlchemyError
        from app.services.analytics_service import AnalyticsService

        def _raise(*args, **kwargs):
            raise SQLAlchemyError("db down")

        monkeypatch.setattr(AnalyticsService, "policy_effectiveness", _raise)
        monkeypatch.setattr(AnalyticsService, "most_triggered_rules", _raise)
        monkeypatch.setattr(AnalyticsService, "most_dangerous_tools", _raise)
        monkeypatch.setattr(AnalyticsService, "blocked_requests", _raise)
        monkeypatch.setattr(AnalyticsService, "hitl_statistics", _raise)
        monkeypatch.setattr(AnalyticsService, "avg_response_time", _raise)
        monkeypatch.setattr(AnalyticsService, "risk_distribution", _raise)
        monkeypatch.setattr(AnalyticsService, "generate_daily_report", _raise)
        monkeypatch.setattr(AnalyticsService, "generate_monthly_report", _raise)
        monkeypatch.setattr(AnalyticsService, "list_reports", _raise)
        monkeypatch.setattr(AnalyticsService, "get_report", _raise)

    def test_query_endpoints_return_500(self, client, auth_headers_factory):
        headers = auth_headers_factory("auditor")
        for path in (
            "/analytics/policy-effectiveness",
            "/analytics/most-triggered-rules",
            "/analytics/most-dangerous-tools",
            "/analytics/blocked-requests",
            "/analytics/hitl-statistics",
            "/analytics/avg-response-time",
            "/analytics/risk-distribution",
            "/analytics/reports",
        ):
            assert client.get(path, headers=headers).status_code == 500

    def test_report_endpoints_return_500(self, client, auth_headers_factory):
        headers = auth_headers_factory("admin")
        assert client.post("/analytics/reports/daily?date=2026-01-01", headers=headers).status_code == 500
        assert client.post("/analytics/reports/monthly?month=2026-01", headers=headers).status_code == 500

    def test_get_report_error_500(self, client, auth_headers_factory):
        assert (
            client.get("/analytics/reports/daily/2026-01-01", headers=auth_headers_factory("auditor")).status_code
            == 500
        )
