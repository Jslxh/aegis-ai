"""Legacy API smoke tests rewritten to run against the in-memory TestClient
instead of a live uvicorn server on localhost:8000."""

import pytest


@pytest.mark.api
class TestAPI:
    def test_root(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"message": "Welcome to Guardrail AI"}

    def test_health(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "healthy"}

    def test_policies(self, client, auth_headers_factory):
        res = client.get("/policies", headers=auth_headers_factory("viewer"))
        assert res.status_code == 200
        assert "rules" in res.json()

    def test_evaluate_allow(self, client, auth_headers_factory):
        res = client.post(
            "/evaluate",
            json={"tool": "database", "action": "delete", "record_count": 5},
            headers=auth_headers_factory("operator"),
        )
        assert res.status_code == 200
        assert res.json()["decision"] == "allow"

    def test_evaluate_block(self, client, auth_headers_factory):
        res = client.post(
            "/evaluate",
            json={"tool": "database", "action": "delete", "record_count": 500},
            headers=auth_headers_factory("operator"),
        )
        assert res.status_code == 200
        body = res.json()
        assert body["decision"] == "block"
        assert body["matched_rule"] == "block_large_delete"

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

    def test_simulate(self, client, auth_headers_factory):
        res = client.get("/simulate", headers=auth_headers_factory("operator"))
        assert res.status_code == 200
        body = res.json()
        assert body["simulation"] == "completed"
        assert "results" in body
