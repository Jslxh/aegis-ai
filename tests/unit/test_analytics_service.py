"""Unit tests for AnalyticsService with PG-only repo methods stubbed out."""

from sqlalchemy.exc import SQLAlchemyError
import pytest

from app.services.analytics_service import AnalyticsService, _iso
from app.database.repositories.analytics_repository import AnalyticsRepository


@pytest.mark.unit
class TestAnalyticsServiceHelpers:
    def test_iso_datetime(self):
        from datetime import datetime

        assert _iso(datetime(2026, 1, 1)) == "2026-01-01T00:00:00"

    def test_iso_fallback(self):
        assert _iso(42) == "42"

    def test_parse_range_branches(self, db_session):
        service = AnalyticsService(db_session)
        from datetime import datetime, timedelta

        assert service._parse_range("1h") >= datetime.utcnow() - timedelta(hours=2)
        assert service._parse_range("24h") >= datetime.utcnow() - timedelta(days=2)
        assert service._parse_range("7d") >= datetime.utcnow() - timedelta(days=8)
        assert service._parse_range("30d") >= datetime.utcnow() - timedelta(days=31)
        assert service._parse_range("all") is None
        assert service._parse_range("garbage") >= datetime.utcnow() - timedelta(days=31)


@pytest.mark.unit
class TestAnalyticsServiceQueries:
    def test_policy_effectiveness_empty(self, db_session):
        result = AnalyticsService(db_session).policy_effectiveness()
        assert result == {"total_rules": 0, "items": []}

    def test_most_triggered_rules_empty(self, db_session):
        assert AnalyticsService(db_session).most_triggered_rules() == {"items": []}

    def test_most_dangerous_tools_empty(self, db_session):
        assert AnalyticsService(db_session).most_dangerous_tools() == {"items": []}

    def test_hitl_statistics_empty(self, db_session):
        result = AnalyticsService(db_session).hitl_statistics()
        assert result["total_requests"] == 0

    def test_risk_distribution_empty(self, db_session):
        result = AnalyticsService(db_session).risk_distribution()
        assert result == {"items": [], "total": 0}


@pytest.mark.unit
class TestAnalyticsReportGeneration:
    def test_generate_daily_report(self, db_session, monkeypatch):
        repo = AnalyticsRepository(db_session)
        monkeypatch.setattr(repo, "blocked_requests", lambda since=None: {"total_blocked": 0})
        monkeypatch.setattr(repo, "avg_response_time", lambda since=None: {"total_requests": 0})

        service = AnalyticsService(db_session)
        service.repo = repo
        report = service.generate_daily_report("2026-01-01")
        assert report["report_type"] == "daily"
        assert report["period"] == "2026-01-01"
        assert report["data"]["blocked_requests"] == {"total_blocked": 0}

    def test_generate_monthly_report_december(self, db_session, monkeypatch):
        repo = AnalyticsRepository(db_session)
        monkeypatch.setattr(repo, "blocked_requests", lambda since=None: {"total_blocked": 0})
        monkeypatch.setattr(repo, "avg_response_time", lambda since=None: {"total_requests": 0})

        service = AnalyticsService(db_session)
        service.repo = repo
        report = service.generate_monthly_report("2026-12")
        assert report["report_type"] == "monthly"
        assert report["period"] == "2026-12"

    def test_generate_monthly_report_non_december(self, db_session, monkeypatch):
        repo = AnalyticsRepository(db_session)
        monkeypatch.setattr(repo, "blocked_requests", lambda since=None: {"total_blocked": 0})
        monkeypatch.setattr(repo, "avg_response_time", lambda since=None: {"total_requests": 0})

        service = AnalyticsService(db_session)
        service.repo = repo
        report = service.generate_monthly_report("2026-02")
        assert report["period"] == "2026-02"

    def test_generate_daily_invalid_date(self, db_session):
        with pytest.raises(ValueError):
            AnalyticsService(db_session).generate_daily_report("not-a-date")

    def test_generate_monthly_invalid_month(self, db_session):
        with pytest.raises(ValueError):
            AnalyticsService(db_session).generate_monthly_report("2026-13")

    def test_upsert_existing_report(self, db_session, monkeypatch):
        repo = AnalyticsRepository(db_session)
        service = AnalyticsService(db_session)
        service.repo = repo
        monkeypatch.setattr(repo, "blocked_requests", lambda since=None: {"total_blocked": 0})
        monkeypatch.setattr(repo, "avg_response_time", lambda since=None: {"total_requests": 0})

        first = service.generate_daily_report("2026-01-01")
        second = service.generate_daily_report("2026-01-01")
        assert first["id"] == second["id"]
        assert len(service.list_reports(report_type="daily")) == 1
        assert service.get_report("daily", "2026-01-01")["period"] == "2026-01-01"
        assert service.get_report("daily", "1999-01-01") is None

    def test_report_uses_only_blocked_response_time(self, db_session, monkeypatch):
        """blocked_requests/avg_response_time return real values in report data."""
        repo = AnalyticsRepository(db_session)
        monkeypatch.setattr(repo, "blocked_requests", lambda since=None: {"total_blocked": 3, "total_requests": 10})
        monkeypatch.setattr(repo, "avg_response_time", lambda since=None: {"total_requests": 10})

        service = AnalyticsService(db_session)
        service.repo = repo
        report = service.generate_daily_report("2026-01-01")
        assert report["data"]["blocked_requests"]["total_blocked"] == 3


@pytest.mark.unit
class TestAnalyticsServiceErrors:
    def test_generate_daily_sqlalchemy_error(self, db_session, monkeypatch):
        def boom(*args, **kwargs):
            raise SQLAlchemyError("boom")

        monkeypatch.setattr(AnalyticsRepository, "blocked_requests", boom)
        monkeypatch.setattr(AnalyticsRepository, "avg_response_time", boom)

        with pytest.raises(SQLAlchemyError):
            AnalyticsService(db_session).generate_daily_report("2026-01-01")
