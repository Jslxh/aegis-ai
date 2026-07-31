"""API tests for AI endpoints (Groq mocked): generation + retrieval + 503 paths."""

import pytest

from app.api import ai_routes
from app.database.repositories.ai_content_repository import AIGeneratedContentRepository
from app.database.repositories.audit_log_repository import AuditLogRepository
from app.database.repositories.execution_history_repository import ExecutionHistoryRepository
from app.database.repositories.simulation_run_repository import SimulationRunRepository


@pytest.mark.api
class TestAiGeneration:
    def test_explain_decision(self, client, auth_headers_factory, mock_groq):
        res = client.post(
            "/ai/explain",
            json={"matched_rule": "r1", "decision": "block", "reason": "too big", "request": {"tool": "db"}},
            headers=auth_headers_factory("operator"),
        )
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_explain_persists_when_execution_id(self, client, auth_headers_factory, session_factory, mock_groq):
        session = session_factory()
        try:
            record = ExecutionHistoryRepository(session).create_record(
                {"tool": "database"}, {"decision": "block", "matched_rule": "r1", "reason": "x"},
                execution_status="blocked",
            )
            session.commit()
            exec_id = record.id
        finally:
            session.close()

        res = client.post(
            "/ai/explain",
            json={
                "matched_rule": "r1",
                "decision": "block",
                "reason": "x",
                "request": {"tool": "database"},
                "execution_id": exec_id,
            },
            headers=auth_headers_factory("operator"),
        )
        assert res.status_code == 200
        session = session_factory()
        try:
            stored = AIGeneratedContentRepository(session).find_by_source("execution", exec_id, content_type="explanation")
            assert stored is not None
            assert stored.source_type == "execution"
        finally:
            session.close()

    def test_risk_analysis(self, client, auth_headers_factory, mock_groq):
        res = client.post(
            "/ai/risk-analysis",
            json={"tool": "database", "action": "delete", "parameters": {"n": 1}, "decision": "block"},
            headers=auth_headers_factory("operator"),
        )
        assert res.status_code == 200

    def test_hitl_summary(self, client, auth_headers_factory, mock_groq):
        res = client.post(
            "/ai/hitl-summary",
            json={"request": {"tool": "email"}, "decision": "require_hitl", "reason": "external"},
            headers=auth_headers_factory("auditor"),
        )
        assert res.status_code == 200

    def test_audit_summary(self, client, auth_headers_factory, mock_groq):
        res = client.post(
            "/ai/audit-summary",
            json={"record": {"tool": "database", "decision": "block"}},
            headers=auth_headers_factory("auditor"),
        )
        assert res.status_code == 200

    def test_simulation_summary(self, client, auth_headers_factory, mock_groq):
        res = client.post(
            "/ai/simulation-summary",
            json={"summary": {"blocked": 1}, "results": []},
            headers=auth_headers_factory("auditor"),
        )
        assert res.status_code == 200

    def test_rbac(self, client, auth_headers_factory, mock_groq):
        assert (
            client.post(
                "/ai/explain",
                json={"decision": "block", "reason": "r", "request": {}},
                headers=auth_headers_factory("viewer"),
            ).status_code
            == 403
        )

    def test_uninitialized_returns_503(self, client, auth_headers_factory, monkeypatch):
        monkeypatch.setattr(ai_routes, "groq", None)
        res = client.post(
            "/ai/explain",
            json={"decision": "block", "reason": "r", "request": {}},
            headers=auth_headers_factory("operator"),
        )
        assert res.status_code == 503


@pytest.mark.api
class TestAiRetrieval:
    def test_execution_explanation_generated(self, client, auth_headers_factory, session_factory, mock_groq):
        session = session_factory()
        try:
            record = ExecutionHistoryRepository(session).create_record(
                {"tool": "database", "action": "delete"},
                {"decision": "block", "matched_rule": "r1", "reason": "too big"},
                execution_status="blocked",
            )
            session.commit()
            exec_id = record.id
        finally:
            session.close()

        res = client.get(f"/ai/executions/{exec_id}/explanation", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        body = res.json()
        assert body["content_type"] == "explanation"
        assert body["source_id"] == exec_id

    def test_execution_explanation_missing_404(self, client, auth_headers_factory, mock_groq):
        res = client.get("/ai/executions/9999/explanation", headers=auth_headers_factory("auditor"))
        assert res.status_code == 404

    def test_audit_summary_retrieval(self, client, auth_headers_factory, session_factory, mock_groq):
        session = session_factory()
        try:
            audit = AuditLogRepository(session).create(
                {"tool": "database"}, {"decision": "block", "matched_rule": "r1", "reason": "x"},
                correlation_id="corr_ai",
            )
            session.commit()
            audit_id = audit.id
        finally:
            session.close()

        res = client.get(f"/ai/audit/{audit_id}/summary", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        assert res.json()["content_type"] == "audit_summary"

    def test_simulation_analysis_retrieval(self, client, auth_headers_factory, session_factory, mock_groq):
        session = session_factory()
        try:
            run = SimulationRunRepository(session).create_run(
                total_scenarios=1, summary={"blocked": 1}, results=[{"scenario": "X"}]
            )
            session.commit()
            run_id = run.id
        finally:
            session.close()

        res = client.get(f"/ai/simulation/{run_id}/analysis", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        assert res.json()["content_type"] == "simulation_analysis"

    def test_retrieval_requires_auditor(self, client, auth_headers_factory, mock_groq):
        assert client.get("/ai/executions/1/explanation", headers=auth_headers_factory("operator")).status_code == 403

    def test_retrieval_uninitialized_503(self, client, auth_headers_factory, session_factory, monkeypatch):
        from app.database.repositories.ai_content_repository import AIGeneratedContentRepository

        session = session_factory()
        try:
            record = ExecutionHistoryRepository(session).create_record(
                {"tool": "database"}, {"decision": "block"}, execution_status="blocked"
            )
            session.commit()
            exec_id = record.id
        finally:
            session.close()

        monkeypatch.setattr(ai_routes, "groq", None)
        res = client.get(f"/ai/executions/{exec_id}/explanation", headers=auth_headers_factory("auditor"))
        assert res.status_code == 503


@pytest.mark.api
class TestAiStoredContent:
    def test_stored_content_served_without_groq(self, client, auth_headers_factory, session_factory, mock_groq):
        from app.database.repositories.ai_content_repository import AIGeneratedContentRepository

        session = session_factory()
        try:
            record = ExecutionHistoryRepository(session).create_record(
                {"tool": "database"}, {"decision": "block"}, execution_status="blocked"
            )
            session.commit()
            exec_id = record.id
            repo = AIGeneratedContentRepository(session)
            repo.create_content(
                content_type="explanation",
                source_type="execution",
                source_id=exec_id,
                explanation="cached explanation",
            )
            session.commit()
        finally:
            session.close()

        res = client.get(f"/ai/executions/{exec_id}/explanation", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        assert res.json()["explanation"] == "cached explanation"
