"""API tests for core endpoints: root, health, evaluate, execute, simulate, dry-run."""

import pytest

from app.database.repositories.audit_log_repository import AuditLogRepository


@pytest.mark.api
class TestBasicEndpoints:
    def test_root(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"message": "Welcome to Guardrail AI"}

    def test_about(self, client):
        res = client.get("/about")
        assert res.status_code == 200
        assert res.json()["project"] == "Guardrail AI"

    def test_health(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "healthy"}


@pytest.mark.api
class TestEvaluate:
    def test_evaluate_allow(self, client, auth_headers_factory):
        headers = auth_headers_factory("operator")
        res = client.post(
            "/evaluate",
            json={"tool": "database", "action": "delete", "record_count": 5},
            headers=headers,
        )
        assert res.status_code == 200
        body = res.json()
        assert body["decision"] == "allow"
        assert body["matched_rule"] is None

    def test_evaluate_block(self, client, auth_headers_factory):
        headers = auth_headers_factory("operator")
        res = client.post(
            "/evaluate",
            json={"tool": "database", "action": "delete", "record_count": 500},
            headers=headers,
        )
        assert res.status_code == 200
        body = res.json()
        assert body["decision"] == "block"
        assert body["matched_rule"] == "block_large_delete"

    def test_evaluate_allows_anonymous(self, client):
        res = client.post(
            "/evaluate",
            json={"tool": "database", "action": "delete", "record_count": 5},
        )
        assert res.status_code == 200

    def test_evaluate_rejects_low_role(self, client, auth_headers_factory):
        res = client.post(
            "/evaluate",
            json={"tool": "database", "action": "delete", "record_count": 5},
            headers=auth_headers_factory("viewer"),
        )
        assert res.status_code == 403

    def test_evaluate_missing_fields_422(self, client, auth_headers_factory):
        res = client.post("/evaluate", json={"tool": "database"}, headers=auth_headers_factory("operator"))
        assert res.status_code == 422


@pytest.mark.api
class TestExecute:
    def test_execute_allow(self, client, auth_headers_factory):
        res = client.post(
            "/execute",
            json={"tool": "database", "action": "delete", "record_count": 5},
            headers=auth_headers_factory("operator"),
        )
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "executed"
        assert body["decision"] == "allow"
        assert body["tool_output"]["status"] == "success"
        assert body["correlation_id"]
        assert body["request_id"]
        assert body["execution_id"]

    def test_execute_block(self, client, auth_headers_factory):
        res = client.post(
            "/execute",
            json={"tool": "database", "action": "delete", "record_count": 500},
            headers=auth_headers_factory("operator"),
        )
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "blocked"
        assert body["decision"] == "block"
        assert body["matched_rule"] == "block_large_delete"
        assert body["tool_output"]["status"] == "Blocked by Guardrail"

    def test_execute_hitl(self, client, auth_headers_factory):
        res = client.post(
            "/execute",
            json={"tool": "email", "action": "send", "external": True},
            headers=auth_headers_factory("operator"),
        )
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "waiting_for_human"
        assert body["decision"] == "require_hitl"
        assert body["matched_rule"] == "external_email_hitl"

    def test_execute_log_and_allow(self, client, auth_headers_factory):
        res = client.post(
            "/execute",
            json={"tool": "file", "action": "read", "path": "docs/confidential.txt"},
            headers=auth_headers_factory("operator"),
        )
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "executed_with_logging"
        assert body["decision"] == "log_and_allow"

    def test_execute_dry_run_query_flag(self, client, auth_headers_factory):
        res = client.post(
            "/execute?dry_run=true",
            json={"tool": "database", "action": "delete", "record_count": 500},
            headers=auth_headers_factory("operator"),
        )
        assert res.status_code == 200
        body = res.json()
        assert body["would_block"] is True
        assert body["risk_level"] == "critical"
        assert body["audit_preview"]["logged"] is False
        assert "simulated_output" in body

    def test_execute_dry_run_allow(self, client, auth_headers_factory):
        res = client.post(
            "/execute",
            json={"tool": "database", "action": "delete", "record_count": 5, "dry_run": True},
            headers=auth_headers_factory("operator"),
        )
        assert res.status_code == 200
        body = res.json()
        assert body["would_execute"] is True
        assert body["would_block"] is False

    def test_execute_writes_audit_and_history(self, client, auth_headers_factory, session_factory):
        client.post(
            "/execute",
            json={"tool": "database", "action": "delete", "record_count": 5},
            headers=auth_headers_factory("operator"),
        )
        session = session_factory()
        try:
            assert AuditLogRepository(session).count({}) == 1
        finally:
            session.close()

    def test_execute_low_role_denied(self, client, auth_headers_factory):
        res = client.post(
            "/execute",
            json={"tool": "database", "action": "delete", "record_count": 5},
            headers=auth_headers_factory("viewer"),
        )
        assert res.status_code == 403


@pytest.mark.api
class TestSimulate:
    def test_simulate_completes(self, client, auth_headers_factory):
        res = client.get("/simulate", headers=auth_headers_factory("operator"))
        assert res.status_code == 200
        body = res.json()
        assert body["simulation"] == "completed"
        assert body["total_scenarios"] == 5
        assert body["summary"]["blocked"] >= 1
        assert len(body["results"]) == 5

    def test_simulate_persists_run(self, client, auth_headers_factory, session_factory):
        client.get("/simulate", headers=auth_headers_factory("operator"))
        session = session_factory()
        try:
            from app.database.repositories.simulation_run_repository import SimulationRunRepository

            runs = SimulationRunRepository(session).list()
            assert len(runs) == 1
            assert runs[0].total_scenarios == 5
        finally:
            session.close()
