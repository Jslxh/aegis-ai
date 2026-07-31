"""API tests for audit endpoints: search, timeline, correlation, integrity, exports."""

import csv
import io
import json

import pytest

from app.database.repositories.audit_log_repository import AuditLogRepository


def _seed_audit(session_factory, n=3):
    session = session_factory()
    try:
        repo = AuditLogRepository(session)
        for i in range(n):
            repo.create(
                {"tool": "database", "action": "delete", "record_count": i},
                {"decision": "block" if i % 2 else "allow", "matched_rule": "r1" if i % 2 else None},
                correlation_id=f"corr_audit_{i}",
                actor="admin",
            )
        session.commit()
    finally:
        session.close()


@pytest.mark.api
class TestAuditSearch:
    def test_search_requires_auditor(self, client, auth_headers_factory):
        assert client.get("/audit/logs", headers=auth_headers_factory("operator")).status_code == 403
        assert client.get("/audit/logs").status_code == 401

    def test_search_empty(self, client, auth_headers_factory):
        res = client.get("/audit/logs", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        assert res.json()["items"] == []
        assert res.json()["total"] == 0

    def test_search_returns_records(self, client, auth_headers_factory, session_factory):
        _seed_audit(session_factory)
        res = client.get("/audit/logs", headers=auth_headers_factory("auditor"))
        body = res.json()
        assert body["total"] == 3
        assert len(body["items"]) == 3

    def test_search_filters(self, client, auth_headers_factory, session_factory):
        _seed_audit(session_factory)
        headers = auth_headers_factory("auditor")
        assert client.get("/audit/logs?decision=block", headers=headers).json()["total"] == 1
        assert client.get("/audit/logs?tool=database", headers=headers).json()["total"] == 3
        assert client.get("/audit/logs?search=corr_audit_0", headers=headers).json()["total"] == 1
        assert client.get("/audit/logs?actor=admin", headers=headers).json()["total"] == 3

    def test_search_pagination(self, client, auth_headers_factory, session_factory):
        _seed_audit(session_factory)
        res = client.get("/audit/logs?page=1&page_size=2", headers=auth_headers_factory("auditor"))
        body = res.json()
        assert len(body["items"]) == 2
        assert body["pages"] == 2

    def test_search_page_size_validation(self, client, auth_headers_factory):
        res = client.get("/audit/logs?page_size=99999", headers=auth_headers_factory("auditor"))
        assert res.status_code == 422


@pytest.mark.api
class TestAuditCorrelationAndIntegrity:
    def test_correlation_chain(self, client, auth_headers_factory, session_factory):
        _seed_audit(session_factory)
        res = client.get("/audit/correlation/corr_audit_0", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["correlation_id"] == "corr_audit_0"

    def test_correlation_missing_returns_empty(self, client, auth_headers_factory):
        res = client.get("/audit/correlation/nope", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        assert res.json() == []

    def test_verify_integrity(self, client, auth_headers_factory, session_factory):
        _seed_audit(session_factory)
        res = client.get("/audit/verify", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        body = res.json()
        assert body["valid"] is True
        assert body["checked"] == 3

    def test_timeline(self, client, auth_headers_factory, session_factory):
        _seed_audit(session_factory)
        res = client.get("/audit/timeline?granularity=day", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        body = res.json()
        assert body["granularity"] == "day"
        assert body["points"]
        assert body["points"][0]["total"] == 3


@pytest.mark.api
class TestAuditExport:
    def test_export_csv(self, client, auth_headers_factory, session_factory):
        _seed_audit(session_factory)
        res = client.get("/audit/export/csv", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/csv")
        assert "attachment" in res.headers["content-disposition"]
        rows = list(csv.DictReader(io.StringIO(res.text)))
        assert len(rows) == 3

    def test_export_json(self, client, auth_headers_factory, session_factory):
        _seed_audit(session_factory)
        res = client.get("/audit/export/json", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("application/json")
        items = json.loads(res.text)
        assert len(items) == 3
        assert items[0]["checksum"]

    def test_export_requires_auditor(self, client, auth_headers_factory):
        assert client.get("/audit/export/csv", headers=auth_headers_factory("operator")).status_code == 403
