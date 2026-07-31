"""End-to-end integration tests chaining the API, services, repositories, and
audit pipeline against the in-memory SQLite database."""

import pytest

from app.database.repositories.audit_log_repository import AuditLogRepository
from app.database.repositories.execution_history_repository import ExecutionHistoryRepository
from app.database.repositories.runtime_metric_repository import RuntimeMetricRepository
from app.database.repositories.simulation_run_repository import SimulationRunRepository
from app.database.repositories.policy_repository import PolicyRepository


def _sample_policy(rule_id: str = "it_custom_block", decision: str = "block") -> dict:
    return {
        "rule_id": rule_id,
        "tool": "database",
        "action": "delete",
        "conditions": [{"field": "record_count", "operator": "gt", "value": 100}],
        "combinator": "AND",
        "decision": decision,
        "message": "Integration test policy",
        "priority": 10,
        "enabled": True,
        "tags": ["it"],
    }


@pytest.mark.api
class TestPolicyCrudRoundTrip:
    def test_create_get_update_toggle_delete(self, client, auth_headers_factory):
        headers = auth_headers_factory("security_analyst")

        created = client.post("/policies", json=_sample_policy(), headers=headers)
        assert created.status_code == 201
        assert created.json()["rule_id"] == "it_custom_block"

        fetched = client.get("/policies/it_custom_block", headers=auth_headers_factory("viewer"))
        assert fetched.status_code == 200
        assert fetched.json()["enabled"] is True

        listed = client.get("/policies", headers=auth_headers_factory("viewer"))
        assert listed.json()["total"] == 1

        toggled = client.post(
            "/policies/it_custom_block/toggle",
            json={"enabled": False},
            headers=headers,
        )
        assert toggled.status_code == 200
        assert toggled.json()["enabled"] is False

        updated = client.put(
            "/policies/it_custom_block",
            json={"message": "updated message", "priority": 5},
            headers=headers,
        )
        assert updated.status_code == 200
        assert updated.json()["message"] == "updated message"
        assert updated.json()["priority"] == 5
        assert updated.json()["version"] >= 2

        deleted = client.delete("/policies/it_custom_block", headers=auth_headers_factory("admin"))
        assert deleted.status_code == 200
        assert client.get("/policies/it_custom_block", headers=auth_headers_factory("viewer")).status_code == 404

    def test_policy_survives_in_db(self, client, auth_headers_factory, session_factory):
        client.post("/policies", json=_sample_policy(), headers=auth_headers_factory("security_analyst"))

        session = session_factory()
        try:
            model = PolicyRepository(session).find_by_rule_id("it_custom_block")
            assert model is not None
            assert model.priority == 10
            assert model.enabled is True
        finally:
            session.close()


@pytest.mark.api
class TestExecuteAuditChain:
    def test_execute_writes_audit_history_and_metric(self, client, auth_headers_factory, session_factory):
        res = client.post(
            "/execute",
            json={"tool": "database", "action": "delete", "record_count": 5},
            headers=auth_headers_factory("operator"),
        )
        assert res.status_code == 200
        body = res.json()
        execution_id = body["execution_id"]
        correlation_id = body["correlation_id"]

        session = session_factory()
        try:
            audits = AuditLogRepository(session).list_recent()
            assert len(audits) == 1
            assert audits[0].execution_id == execution_id
            assert audits[0].correlation_id == correlation_id
            assert audits[0].decision == "allow"

            history = ExecutionHistoryRepository(session).list_recent()
            assert len(history) == 1
            assert history[0].execution_id == execution_id
            assert history[0].execution_status == "executed"

            metric = RuntimeMetricRepository(session).recent_activity(limit=10)
            assert len(metric) == 1
            assert metric[0].execution_id == execution_id
            assert metric[0].decision == "allow"
        finally:
            session.close()

    def test_blocked_execution_links_by_correlation(self, client, auth_headers_factory, session_factory):
        res = client.post(
            "/execute",
            json={"tool": "database", "action": "delete", "record_count": 500},
            headers=auth_headers_factory("operator"),
        )
        assert res.status_code == 200
        correlation_id = res.json()["correlation_id"]

        session = session_factory()
        try:
            linked = AuditLogRepository(session).find_by_correlation_id(correlation_id)
            assert len(linked) == 1
            assert linked[0].decision == "block"
            assert linked[0].matched_rule == "block_large_delete"
        finally:
            session.close()

    def test_audit_chain_integrity(self, client, auth_headers_factory, session_factory):
        for i in range(3):
            client.post(
                "/execute",
                json={"tool": "database", "action": "delete", "record_count": 5 + i},
                headers=auth_headers_factory("operator"),
            )

        session = session_factory()
        try:
            result = AuditLogRepository(session).verify_integrity()
            assert result["valid"] is True
            assert result["checked"] == 3
            assert result["errors"] == []
        finally:
            session.close()

    def test_simulate_persists_run_with_results(self, client, auth_headers_factory, session_factory):
        res = client.get("/simulate", headers=auth_headers_factory("operator"))
        assert res.status_code == 200
        body = res.json()
        assert body["simulation"] == "completed"
        assert body["total_scenarios"] == 5

        session = session_factory()
        try:
            runs = SimulationRunRepository(session).list_recent()
            assert len(runs) == 1
            assert runs[0].total_scenarios == 5
            assert len(runs[0].results) == 5
        finally:
            session.close()


@pytest.mark.api
class TestImportExportRoundTrip:
    def test_import_then_export_roundtrip(self, client, auth_headers_factory):
        yaml_body = """
rules:
  - id: it_imported
    tool: email
    action: send
    conditions:
      - field: recipient_count
        operator: gt
        value: 50
    combinator: AND
    decision: require_hitl
    message: Imported bulk email needs approval
    priority: 5
    enabled: true
"""
        imported = client.post(
            "/policies/import",
            content=yaml_body,
            headers=auth_headers_factory("admin"),
        )
        assert imported.status_code == 200
        assert imported.json()["created"] == 1
        assert imported.json()["errors"] == []

        exported = client.get("/policies/export", headers=auth_headers_factory("auditor"))
        assert exported.status_code == 200
        rule_ids = [p["id"] for p in exported.json()["policies"]]
        assert "it_imported" in rule_ids

        listed = client.get("/policies", headers=auth_headers_factory("viewer"))
        assert listed.json()["total"] == 1


@pytest.mark.api
class TestRbacAcrossPipeline:
    def test_role_gates_full_pipeline(self, client, auth_headers_factory):
        viewer = auth_headers_factory("viewer")
        operator = auth_headers_factory("operator")
        security_analyst = auth_headers_factory("security_analyst")
        auditor = auth_headers_factory("auditor")
        admin = auth_headers_factory("admin")

        assert client.post("/policies", json=_sample_policy(), headers=viewer).status_code == 403
        assert client.post("/policies", json=_sample_policy(), headers=security_analyst).status_code == 201

        assert client.get("/policies", headers=viewer).status_code == 200
        assert client.post("/execute", json={"tool": "database", "action": "delete", "record_count": 5}, headers=viewer).status_code == 403
        assert client.post("/execute", json={"tool": "database", "action": "delete", "record_count": 5}, headers=operator).status_code == 200

        assert client.get("/audit", headers=auditor).status_code == 200
        assert client.get("/audit", headers=viewer).status_code == 403

        assert client.delete("/policies/it_custom_block", headers=security_analyst).status_code == 403
        assert client.delete("/policies/it_custom_block", headers=admin).status_code == 200

        assert client.get("/policies", headers=auth_headers_factory("viewer")).json()["total"] == 0
