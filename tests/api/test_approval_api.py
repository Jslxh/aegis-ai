"""API tests for the human-in-the-loop approval workflow."""

import pytest

from app.database.repositories.hitl_request_repository import HITLRequestRepository

HITL_REQUEST = {"tool": "database", "action": "delete", "record_count": 500}


def _create_request(session_factory, request_id="hitl-1", expires_at=None):
    session = session_factory()
    try:
        repo = HITLRequestRepository(session)
        repo.create_request(request_id, HITL_REQUEST, "require_hitl", "bulk delete", expires_at=expires_at)
        session.commit()
    finally:
        session.close()


@pytest.mark.api
class TestApprovalList:
    def test_list_pending_default(self, client, auth_headers_factory, session_factory):
        _create_request(session_factory, "hitl-1")
        _create_request(session_factory, "hitl-2")
        res = client.get("/approvals", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 2
        assert all(item["status"] == "pending" for item in body["items"])
        assert body["items"][0]["request_data"]["tool"] == "database"

    def test_list_status_and_tool_filters(self, client, auth_headers_factory, session_factory):
        _create_request(session_factory, "hitl-1")
        session = session_factory()
        try:
            repo = HITLRequestRepository(session)
            repo.approve("hitl-1", reviewer="admin")
            repo.create_request("hitl-2", {"tool": "email", "action": "send"}, "require_hitl", None)
            session.commit()
        finally:
            session.close()
        headers = auth_headers_factory("auditor")
        assert client.get("/approvals?status=approved", headers=headers).json()["total"] == 1
        assert client.get("/approvals?status=all", headers=headers).json()["total"] == 2
        assert client.get("/approvals?tool=email", headers=headers).json()["total"] == 1
        assert client.get("/approvals?status=invalid", headers=headers).status_code == 422

    def test_list_requires_auth(self, client):
        assert client.get("/approvals").status_code == 401

    def test_list_requires_auditor_role(self, client, auth_headers_factory):
        assert client.get("/approvals", headers=auth_headers_factory("viewer")).status_code == 403

    def test_list_pagination(self, client, auth_headers_factory, session_factory):
        for i in range(5):
            _create_request(session_factory, f"hitl-{i}")
        headers = auth_headers_factory("auditor")
        body = client.get("/approvals?page=2&page_size=2", headers=headers).json()
        assert body["total"] == 5
        assert body["pages"] == 3
        assert len(body["items"]) == 2


@pytest.mark.api
class TestApprovalGet:
    def test_get_by_request_id(self, client, auth_headers_factory, session_factory):
        _create_request(session_factory, "hitl-1")
        res = client.get("/approvals/hitl-1", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        body = res.json()
        assert body["request_id"] == "hitl-1"
        assert body["policy_decision"] == "require_hitl"

    def test_get_missing(self, client, auth_headers_factory):
        res = client.get("/approvals/nope", headers=auth_headers_factory("auditor"))
        assert res.status_code == 404

    def test_get_requires_auditor(self, client, auth_headers_factory, session_factory):
        _create_request(session_factory, "hitl-1")
        assert client.get("/approvals/hitl-1", headers=auth_headers_factory("operator")).status_code == 403


@pytest.mark.api
class TestApprovalApprove:
    def test_approve_updates_workflow_fields(self, client, auth_headers_factory, session_factory):
        _create_request(session_factory, "hitl-1")
        res = client.post(
            "/approvals/hitl-1/approve",
            json={"reason": "looks safe", "comments": "approving"},
            headers=auth_headers_factory("security_analyst"),
        )
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "approved"
        assert body["reviewer"] == "security_analyst"
        assert body["comments"] == "approving"
        assert body["approval_reason"] == "looks safe"
        assert body["approved_at"] is not None

    def test_approve_twice_conflicts(self, client, auth_headers_factory, session_factory):
        _create_request(session_factory, "hitl-1")
        headers = auth_headers_factory("security_analyst")
        assert client.post("/approvals/hitl-1/approve", json={}, headers=headers).status_code == 200
        assert client.post("/approvals/hitl-1/approve", json={}, headers=headers).status_code == 409

    def test_approve_after_reject_conflicts(self, client, auth_headers_factory, session_factory):
        _create_request(session_factory, "hitl-1")
        headers = auth_headers_factory("security_analyst")
        client.post("/approvals/hitl-1/reject", json={"reason": "no"}, headers=headers)
        assert client.post("/approvals/hitl-1/approve", json={}, headers=headers).status_code == 409

    def test_approve_missing(self, client, auth_headers_factory):
        res = client.post("/approvals/nope/approve", json={}, headers=auth_headers_factory("security_analyst"))
        assert res.status_code == 404

    def test_approve_requires_security_analyst(self, client, auth_headers_factory, session_factory):
        _create_request(session_factory, "hitl-1")
        assert client.post(
            "/approvals/hitl-1/approve", json={}, headers=auth_headers_factory("auditor")
        ).status_code == 403


@pytest.mark.api
class TestApprovalReject:
    def test_reject_updates_workflow_fields(self, client, auth_headers_factory, session_factory):
        _create_request(session_factory, "hitl-1")
        res = client.post(
            "/approvals/hitl-1/reject",
            json={"reason": "blocked", "comments": "not allowed"},
            headers=auth_headers_factory("security_analyst"),
        )
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "rejected"
        assert body["reviewer"] == "security_analyst"
        assert body["rejected_at"] is not None

    def test_reject_after_approve_conflicts(self, client, auth_headers_factory, session_factory):
        _create_request(session_factory, "hitl-1")
        headers = auth_headers_factory("security_analyst")
        client.post("/approvals/hitl-1/approve", json={}, headers=headers)
        assert client.post("/approvals/hitl-1/reject", json={}, headers=headers).status_code == 409

    def test_reject_missing(self, client, auth_headers_factory):
        res = client.post("/approvals/nope/reject", json={}, headers=auth_headers_factory("security_analyst"))
        assert res.status_code == 404


@pytest.mark.api
class TestApprovalExpiry:
    def test_approve_expired_request_gone(self, client, auth_headers_factory, session_factory):
        from datetime import datetime, timedelta, timezone

        past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
        _create_request(session_factory, "hitl-1", expires_at=past)
        res = client.post(
            "/approvals/hitl-1/approve", json={}, headers=auth_headers_factory("security_analyst")
        )
        assert res.status_code == 410
        session = session_factory()
        try:
            assert HITLRequestRepository(session).find_by_request_id("hitl-1").status == "expired"
        finally:
            session.close()

    def test_expire_endpoint(self, client, auth_headers_factory, session_factory):
        _create_request(session_factory, "hitl-1")
        res = client.post("/approvals/hitl-1/expire", json={}, headers=auth_headers_factory("security_analyst"))
        assert res.status_code == 200
        assert res.json()["status"] == "expired"


@pytest.mark.api
class TestApprovalStats:
    def test_stats(self, client, auth_headers_factory, session_factory):
        _create_request(session_factory, "hitl-1")
        session = session_factory()
        try:
            repo = HITLRequestRepository(session)
            repo.approve("hitl-1", reviewer="admin")
            repo.create_request("hitl-2", {"tool": "email", "action": "send"}, "require_hitl", None)
            repo.create_request("hitl-3", {"tool": "email", "action": "send"}, "require_hitl", None)
            repo.reject("hitl-3", reviewer="admin")
            session.commit()
        finally:
            session.close()
        res = client.get("/approvals/stats", headers=auth_headers_factory("auditor"))
        assert res.status_code == 200
        body = res.json()
        assert body["total_requests"] == 3
        assert body["pending"] == 1
        assert body["approved"] == 1
        assert body["rejected"] == 1
        assert body["approval_rate_pct"] == pytest.approx(33.3, abs=0.1)

    def test_stats_requires_auditor(self, client, auth_headers_factory):
        assert client.get("/approvals/stats", headers=auth_headers_factory("viewer")).status_code == 403
