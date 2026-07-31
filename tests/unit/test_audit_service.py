"""Unit tests for the audit service: tracing IDs, filters, export, integrity."""

import csv
import io
import json

import pytest

from app.services.audit_service import AuditService


@pytest.mark.unit
class TestTraceIdGeneration:
    def test_correlation_id_prefix(self):
        cid = AuditService.generate_correlation_id()
        assert cid.startswith("corr_")
        assert len(cid) == 5 + 32

    def test_request_id_prefix(self):
        assert AuditService.generate_request_id().startswith("req_")

    def test_execution_id_prefix(self):
        assert AuditService.generate_execution_id().startswith("exec_")

    def test_ids_are_unique(self):
        ids = {AuditService.generate_correlation_id() for _ in range(100)}
        assert len(ids) == 100


@pytest.mark.unit
class TestBuildFilters:
    def test_all_filters_forwarded(self):
        filters = AuditService._build_filters(
            tool="database",
            action="delete",
            decision="block",
            status="blocked",
            event_type="policy",
            risk_level="critical",
            correlation_id="corr_1",
            request_id="req_1",
            execution_id="exec_1",
            source="api",
            actor="admin",
            search="users",
            start_date="2026-01-01T00:00:00",
            end_date="2026-01-02T00:00:00",
        )
        assert filters["tool"] == "database"
        assert filters["search"] == "users"
        assert filters["start_date"].year == 2026
        assert filters["end_date"].year == 2026

    def test_empty_filters(self):
        assert AuditService._build_filters() == {}

    def test_invalid_dates_ignored(self):
        filters = AuditService._build_filters(start_date="not-a-date")
        assert "start_date" not in filters


@pytest.mark.unit
class TestAuditServiceWithDb:
    def test_create_and_search(self, db_session):
        from app.database.repositories.audit_log_repository import AuditLogRepository

        repo = AuditLogRepository(db_session)
        repo.create(
            {"tool": "database", "action": "delete", "record_count": 5},
            {"decision": "allow", "matched_rule": None, "reason": "ok"},
            correlation_id="corr_abc",
        )
        db_session.commit()

        service = AuditService(db_session)
        result = service.search(page=1, page_size=50)
        assert result["total"] == 1
        assert result["items"][0]["tool"] == "database"
        assert result["items"][0]["correlation_id"] == "corr_abc"
        assert result["pages"] == 1

    def test_search_filter_and_pagination(self, db_session):
        from app.database.repositories.audit_log_repository import AuditLogRepository

        repo = AuditLogRepository(db_session)
        for i in range(5):
            repo.create(
                {"tool": "database", "action": "delete", "record_count": i},
                {"decision": "block", "matched_rule": "r1", "reason": f"blocked {i}"},
                correlation_id=f"corr_{i}",
            )
        db_session.commit()

        service = AuditService(db_session)
        result = service.search(page=1, page_size=2, decision="block")
        assert result["total"] == 5
        assert len(result["items"]) == 2
        assert result["pages"] == 3

        page3 = service.search(page=3, page_size=2, decision="block")
        assert len(page3["items"]) == 1

    def test_page_size_capped(self, db_session):
        service = AuditService(db_session)
        result = service.search(page_size=99999)
        assert result["page_size"] == 500

    def test_by_correlation(self, db_session):
        from app.database.repositories.audit_log_repository import AuditLogRepository

        repo = AuditLogRepository(db_session)
        repo.create({"tool": "a", "action": "x"}, {"decision": "allow"}, correlation_id="corr_x")
        repo.create({"tool": "b", "action": "y"}, {"decision": "allow"}, correlation_id="corr_y")
        repo.create({"tool": "c", "action": "z"}, {"decision": "allow"}, correlation_id="corr_x")
        db_session.commit()

        service = AuditService(db_session)
        items = service.by_correlation("corr_x")
        assert len(items) == 2
        assert all(i["correlation_id"] == "corr_x" for i in items)

    def test_export_csv(self, db_session):
        from app.database.repositories.audit_log_repository import AuditLogRepository

        repo = AuditLogRepository(db_session)
        repo.create(
            {"tool": "database", "action": "delete"},
            {"decision": "allow", "matched_rule": None, "reason": "ok"},
            correlation_id="corr_csv",
        )
        db_session.commit()

        service = AuditService(db_session)
        content = service.export_csv({}, limit=100)
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["correlation_id"] == "corr_csv"
        assert rows[0]["decision"] == "allow"

    def test_export_json(self, db_session):
        from app.database.repositories.audit_log_repository import AuditLogRepository

        repo = AuditLogRepository(db_session)
        repo.create(
            {"tool": "database", "action": "delete"},
            {"decision": "block", "matched_rule": "r1", "reason": "no"},
            correlation_id="corr_json",
        )
        db_session.commit()

        service = AuditService(db_session)
        items = service.export_json({}, limit=100)
        assert items[0]["correlation_id"] == "corr_json"
        assert items[0]["checksum"]

    def test_verify_integrity_valid(self, db_session):
        from app.database.repositories.audit_log_repository import AuditLogRepository

        repo = AuditLogRepository(db_session)
        for i in range(3):
            repo.create(
                {"tool": "database", "action": "delete", "n": i},
                {"decision": "allow", "matched_rule": None, "reason": "ok"},
                correlation_id=f"corr_{i}",
            )
        db_session.commit()

        service = AuditService(db_session)
        result = service.verify_integrity()
        assert result["valid"] is True
        assert result["checked"] == 3
        assert result["errors"] == []

    def test_serialize_omits_checksum_gap_fields(self, db_session):
        from app.database.repositories.audit_log_repository import AuditLogRepository

        repo = AuditLogRepository(db_session)
        model = repo.create({"tool": "database", "action": "delete"}, {"decision": "allow"})
        db_session.commit()

        serialized = AuditService._serialize(model)
        assert set(serialized) >= {
            "id", "timestamp", "event_type", "status", "tool", "action",
            "decision", "matched_rule", "reason", "risk_level",
            "correlation_id", "request_id", "execution_id", "source",
            "actor", "client_ip", "user_agent", "checksum", "prev_checksum",
        }
