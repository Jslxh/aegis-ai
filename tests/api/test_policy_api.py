"""API tests for policy management CRUD, RBAC, import/export, and validation."""

import pytest

from app.database.repositories.policy_repository import PolicyRepository

VALID_POLICY = {
    "rule_id": "test_block_delete",
    "tool": "database",
    "action": "delete",
    "conditions": [{"field": "record_count", "operator": ">", "value": 100}],
    "combinator": "AND",
    "decision": "block",
    "message": "Test policy",
    "priority": 5,
}


@pytest.mark.api
class TestPolicyList:
    def test_list_empty(self, client, auth_headers_factory):
        res = client.get("/policies", headers=auth_headers_factory("viewer"))
        assert res.status_code == 200
        assert res.json()["rules"] == []

    def test_list_requires_auth(self, client):
        assert client.get("/policies").status_code == 401

    def test_list_after_create(self, client, auth_headers_factory, session_factory):
        session = session_factory()
        try:
            PolicyRepository(session).create_policy(VALID_POLICY)
            session.commit()
        finally:
            session.close()
        res = client.get("/policies", headers=auth_headers_factory("viewer"))
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 1
        assert body["enabled_count"] == 1

    def test_list_filters(self, client, auth_headers_factory, session_factory):
        session = session_factory()
        try:
            repo = PolicyRepository(session)
            repo.create_policy(VALID_POLICY)
            repo.create_policy({**VALID_POLICY, "rule_id": "r2", "tool": "email", "action": "send", "enabled": False})
            session.commit()
        finally:
            session.close()
        headers = auth_headers_factory("viewer")
        assert client.get("/policies?tool=database", headers=headers).json()["total"] == 1
        assert client.get("/policies?enabled_only=true", headers=headers).json()["total"] == 1
        assert client.get("/policies?action=send", headers=headers).json()["total"] == 1


@pytest.mark.api
class TestPolicyCrud:
    def test_create_policy(self, client, auth_headers_factory):
        res = client.post("/policies", json=VALID_POLICY, headers=auth_headers_factory("security_analyst"))
        assert res.status_code == 201
        body = res.json()
        assert body["rule_id"] == "test_block_delete"
        assert body["version"] == 1

    def test_create_duplicate_returns_409(self, client, auth_headers_factory, session_factory):
        session = session_factory()
        try:
            PolicyRepository(session).create_policy(VALID_POLICY)
            session.commit()
        finally:
            session.close()
        res = client.post("/policies", json=VALID_POLICY, headers=auth_headers_factory("security_analyst"))
        assert res.status_code == 409

    def test_create_invalid_returns_422(self, client, auth_headers_factory):
        res = client.post(
            "/policies",
            json={"rule_id": "r", "tool": "db", "action": "x", "decision": "bananas", "message": "m"},
            headers=auth_headers_factory("security_analyst"),
        )
        assert res.status_code == 422

    def test_create_conflict_returns_warnings(self, client, auth_headers_factory, session_factory):
        session = session_factory()
        try:
            PolicyRepository(session).create_policy({**VALID_POLICY, "rule_id": "existing_block"})
            session.commit()
        finally:
            session.close()
        res = client.post(
            "/policies",
            json={**VALID_POLICY, "rule_id": "new_allow", "decision": "allow"},
            headers=auth_headers_factory("security_analyst"),
        )
        assert res.status_code == 201
        assert "warnings" in res.json()

    def test_create_requires_role(self, client, auth_headers_factory):
        assert client.post("/policies", json=VALID_POLICY, headers=auth_headers_factory("operator")).status_code == 403
        assert client.post("/policies", json=VALID_POLICY, headers=auth_headers_factory("viewer")).status_code == 403

    def test_get_policy(self, client, auth_headers_factory, session_factory):
        session = session_factory()
        try:
            PolicyRepository(session).create_policy(VALID_POLICY)
            session.commit()
        finally:
            session.close()
        res = client.get("/policies/test_block_delete", headers=auth_headers_factory("viewer"))
        assert res.status_code == 200
        assert res.json()["rule_id"] == "test_block_delete"

    def test_get_policy_not_found(self, client, auth_headers_factory):
        assert client.get("/policies/missing", headers=auth_headers_factory("viewer")).status_code == 404

    def test_update_policy(self, client, auth_headers_factory, session_factory):
        session = session_factory()
        try:
            PolicyRepository(session).create_policy(VALID_POLICY)
            session.commit()
        finally:
            session.close()
        res = client.put(
            "/policies/test_block_delete",
            json={"decision": "require_hitl", "message": "Updated"},
            headers=auth_headers_factory("security_analyst"),
        )
        assert res.status_code == 200
        body = res.json()
        assert body["decision"] == "require_hitl"
        assert body["version"] == 2

    def test_update_missing_returns_404(self, client, auth_headers_factory):
        res = client.put(
            "/policies/nope",
            json={"decision": "allow"},
            headers=auth_headers_factory("security_analyst"),
        )
        assert res.status_code == 404

    def test_toggle_policy(self, client, auth_headers_factory, session_factory):
        session = session_factory()
        try:
            PolicyRepository(session).create_policy(VALID_POLICY)
            session.commit()
        finally:
            session.close()
        res = client.post(
            "/policies/test_block_delete/toggle",
            json={"enabled": False},
            headers=auth_headers_factory("security_analyst"),
        )
        assert res.status_code == 200
        assert res.json()["enabled"] is False

    def test_toggle_missing_returns_404(self, client, auth_headers_factory):
        res = client.post(
            "/policies/nope/toggle",
            json={"enabled": False},
            headers=auth_headers_factory("security_analyst"),
        )
        assert res.status_code == 404

    def test_delete_policy(self, client, auth_headers_factory, session_factory):
        session = session_factory()
        try:
            PolicyRepository(session).create_policy(VALID_POLICY)
            session.commit()
        finally:
            session.close()
        res = client.delete("/policies/test_block_delete", headers=auth_headers_factory("admin"))
        assert res.status_code == 200
        assert res.json()["deleted"] is True

    def test_delete_requires_admin(self, client, auth_headers_factory, session_factory):
        session = session_factory()
        try:
            PolicyRepository(session).create_policy(VALID_POLICY)
            session.commit()
        finally:
            session.close()
        assert client.delete("/policies/test_block_delete", headers=auth_headers_factory("security_analyst")).status_code == 403

    def test_delete_missing_returns_404(self, client, auth_headers_factory):
        assert client.delete("/policies/nope", headers=auth_headers_factory("admin")).status_code == 404


@pytest.mark.api
class TestPolicyValidation:
    def test_validate_valid(self, client, auth_headers_factory):
        res = client.post("/policies/validate", json=VALID_POLICY, headers=auth_headers_factory("operator"))
        assert res.status_code == 200
        assert res.json()["valid"] is True

    def test_validate_invalid(self, client, auth_headers_factory):
        res = client.post(
            "/policies/validate",
            json={"rule_id": "r", "tool": "db", "action": "x", "decision": "nope", "message": "m"},
            headers=auth_headers_factory("operator"),
        )
        assert res.status_code == 200
        assert res.json()["valid"] is False
        assert res.json()["errors"]

    def test_check_conflicts(self, client, auth_headers_factory, session_factory):
        session = session_factory()
        try:
            PolicyRepository(session).create_policy({**VALID_POLICY, "rule_id": "existing_block"})
            session.commit()
        finally:
            session.close()
        res = client.post(
            "/policies/check-conflicts",
            json={**VALID_POLICY, "rule_id": "new_allow", "decision": "allow"},
            headers=auth_headers_factory("operator"),
        )
        assert res.status_code == 200
        assert len(res.json()) == 1

    def test_preview_rule(self, client, auth_headers_factory):
        payload = {
            "policy": VALID_POLICY,
            "request": {"tool": "database", "action": "delete", "record_count": 500},
        }
        res = client.post("/policies/preview", json=payload, headers=auth_headers_factory("operator"))
        assert res.status_code == 200
        assert res.json()["decision"] == "block"


@pytest.mark.api
class TestPolicyImportExport:
    def test_export_yaml_roundtrip(self, client, auth_headers_factory, session_factory):
        session = session_factory()
        try:
            PolicyRepository(session).create_policy(VALID_POLICY)
            session.commit()
        finally:
            session.close()
        headers = auth_headers_factory("auditor")
        res = client.get("/policies/export", headers=headers)
        assert res.status_code == 200
        assert res.json()["format"] == "yaml"
        assert len(res.json()["policies"]) == 1

    def test_export_yaml_download(self, client, auth_headers_factory, session_factory):
        session = session_factory()
        try:
            PolicyRepository(session).create_policy(VALID_POLICY)
            session.commit()
        finally:
            session.close()
        res = client.get("/policies/export/yaml", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/yaml")
        assert "test_block_delete" in res.text

    def test_import_policies(self, client, auth_headers_factory):
        yaml_body = """
rules:
  - id: imported_rule
    tool: database
    action: delete
    decision: block
    message: Imported
"""
        res = client.post(
            "/policies/import",
            content=yaml_body,
            headers={"Content-Type": "text/plain", **auth_headers_factory("admin")},
        )
        assert res.status_code == 200
        assert res.json()["created"] == 1

    def test_import_invalid_yaml(self, client, auth_headers_factory):
        res = client.post(
            "/policies/import",
            content="not: [valid yaml",
            headers={"Content-Type": "text/plain", **auth_headers_factory("admin")},
        )
        assert res.status_code == 400

    def test_import_requires_admin(self, client, auth_headers_factory):
        res = client.post(
            "/policies/import",
            content="rules: []",
            headers={"Content-Type": "text/plain", **auth_headers_factory("auditor")},
        )
        assert res.status_code == 403
