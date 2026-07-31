"""Repository + PG-backed queue tests for the HITL request model."""

import pytest

from app.hitl.approval import PgApprovalQueue
from app.database.repositories.hitl_request_repository import HITLRequestRepository


@pytest.mark.repo
class TestHITLRequestRepository:
    def test_create_request(self, db_session):
        repo = HITLRequestRepository(db_session)
        model = repo.create_request(
            "req-1", {"tool": "database", "action": "delete"}, "require_hitl", "bulk delete"
        )
        assert model.status == "pending"
        assert model.tool == "database"
        assert model.policy_decision == "require_hitl"

    def test_find_by_request_id(self, db_session):
        repo = HITLRequestRepository(db_session)
        repo.create_request("req-1", {"tool": "email", "action": "send"}, "require_hitl", None)
        found = repo.find_by_request_id("req-1")
        assert found is not None
        assert found.request_data["tool"] == "email"
        assert repo.find_by_request_id("missing") is None

    def test_list_pending_only(self, db_session):
        repo = HITLRequestRepository(db_session)
        repo.create_request("req-1", {"tool": "db"}, "require_hitl", None)
        repo.create_request("req-2", {"tool": "db"}, "require_hitl", None)
        repo.approve("req-2")
        pending = repo.list_pending()
        assert [r.request_id for r in pending] == ["req-1"]

    def test_approve_updates_status_and_reason(self, db_session):
        repo = HITLRequestRepository(db_session)
        repo.create_request("req-1", {"tool": "db"}, "require_hitl", None)
        model = repo.approve("req-1", "approved by admin")
        assert model.status == "approved"
        assert model.approval_reason == "approved by admin"
        assert repo.approve("missing") is None

    def test_reject_updates_status_and_reason(self, db_session):
        repo = HITLRequestRepository(db_session)
        repo.create_request("req-1", {"tool": "db"}, "require_hitl", None)
        model = repo.reject("req-1", "denied")
        assert model.status == "rejected"
        assert model.approval_reason == "denied"
        assert repo.reject("missing") is None

    def test_approve_sets_reviewer_comments_and_timestamp(self, db_session):
        repo = HITLRequestRepository(db_session)
        repo.create_request("req-1", {"tool": "db"}, "require_hitl", None)
        model = repo.approve("req-1", "ok", reviewer="alice", comments="looks safe")
        assert model.status == "approved"
        assert model.reviewer == "alice"
        assert model.comments == "looks safe"
        assert model.approved_at is not None
        assert model.rejected_at is None

    def test_reject_sets_reviewer_comments_and_timestamp(self, db_session):
        repo = HITLRequestRepository(db_session)
        repo.create_request("req-1", {"tool": "email"}, "require_hitl", None)
        model = repo.reject("req-1", "nope", reviewer="bob", comments="policy violation")
        assert model.status == "rejected"
        assert model.reviewer == "bob"
        assert model.comments == "policy violation"
        assert model.rejected_at is not None
        assert model.approved_at is None

    def test_resolution_is_idempotent_guard(self, db_session):
        repo = HITLRequestRepository(db_session)
        repo.create_request("req-1", {"tool": "db"}, "require_hitl", None)
        repo.approve("req-1")
        model = repo.approve("req-1", "second approve")
        assert model.approval_reason != "second approve"

    def test_expire_moves_pending_to_expired(self, db_session):
        from datetime import datetime, timedelta, timezone

        repo = HITLRequestRepository(db_session)
        repo.create_request(
            "req-1",
            {"tool": "db"},
            "require_hitl",
            None,
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),
        )
        model = repo.expire("req-1")
        assert model.status == "expired"
        assert repo.expire("missing") is None

    def test_expire_stale_only_touches_past_deadlines(self, db_session):
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        repo = HITLRequestRepository(db_session)
        repo.create_request("old", {"tool": "a"}, "require_hitl", None, expires_at=now - timedelta(hours=2))
        repo.create_request("fresh", {"tool": "b"}, "require_hitl", None, expires_at=now + timedelta(hours=2))
        repo.create_request("no-deadline", {"tool": "c"}, "require_hitl", None)
        expired = repo.expire_stale(now=now)
        assert expired == 1
        assert repo.find_by_request_id("old").status == "expired"
        assert repo.find_by_request_id("fresh").status == "pending"
        assert repo.find_by_request_id("no-deadline").status == "pending"

    def test_list_requests_filters_and_paginates(self, db_session):
        repo = HITLRequestRepository(db_session)
        for i in range(5):
            repo.create_request(f"req-{i}", {"tool": "db"}, "require_hitl", None)
        repo.approve("req-0")
        pending = repo.list_requests(status="pending")
        assert len(pending) == 4
        approved = repo.list_requests(status="approved")
        assert len(approved) == 1
        paged = repo.list_requests(status="pending", skip=1, limit=2)
        assert len(paged) == 2
        assert repo.count_requests(status="pending") == 4

    def test_stats_aggregates(self, db_session):
        repo = HITLRequestRepository(db_session)
        for i in range(3):
            repo.create_request(f"req-{i}", {"tool": "db"}, "require_hitl", None)
        repo.approve("req-0")
        repo.reject("req-1")
        stats = repo.stats()
        assert stats["total_requests"] == 3
        assert stats["pending"] == 1
        assert stats["approved"] == 1
        assert stats["rejected"] == 1
        assert stats["approval_rate_pct"] == pytest.approx(33.3, abs=0.1)
        assert stats["by_tool"]["db"] == 3

    def test_get_by_id(self, db_session):
        repo = HITLRequestRepository(db_session)
        created = repo.create_request("req-1", {"tool": "db"}, "require_hitl", None)
        assert repo.get_by_id(created.id).request_id == "req-1"
        assert repo.get_by_id(99999) is None


@pytest.mark.repo
class TestPgApprovalQueue:
    def test_full_lifecycle(self, session_factory):
        q = PgApprovalQueue(session_factory)

        created = q.request_approval("pg-1", {"tool": "database", "action": "delete"}, "require_hitl", "risk")
        assert created is False

        pending = q.get_pending_requests()
        assert len(pending) == 1
        assert pending[0]["request_id"] == "pg-1"
        assert pending[0]["status"] == "pending"
        assert pending[0]["policy_decision"] == "require_hitl"
        assert pending[0]["request_data"]["tool"] == "database"

        q.approve("pg-1", "ok")
        assert q.get_pending_requests() == []

        session = session_factory()
        try:
            from app.database.models.hitl_request import HITLRequestModel

            model = session.query(HITLRequestModel).filter_by(request_id="pg-1").first()
            assert model.status == "approved"
            assert model.approval_reason == "ok"
        finally:
            session.close()

    def test_reject_flow(self, session_factory):
        q = PgApprovalQueue(session_factory)
        q.request_approval("pg-2", {"tool": "file"}, "require_hitl", "risk")
        q.reject("pg-2", "blocked by policy")
        assert q.get_pending_requests() == []

    def test_approve_missing_is_noop(self, session_factory):
        q = PgApprovalQueue(session_factory)
        q.approve("nope")
        assert q.get_pending_requests() == []


@pytest.mark.repo
class TestPgApprovalQueueErrorPaths:
    def _failing_session(self):
        class FailingSession:
            def __init__(self):
                self.rolled_back = False

            def commit(self):
                raise RuntimeError("commit failed")

            def rollback(self):
                self.rolled_back = True

            def close(self):
                pass

        return FailingSession()

    def test_request_approval_rolls_back_on_commit_error(self, monkeypatch):
        import app.hitl.approval as approval_mod

        failing = self._failing_session()
        q = PgApprovalQueue(lambda: failing)
        from app.database.repositories.hitl_request_repository import HITLRequestRepository

        monkeypatch.setattr(HITLRequestRepository, "create_request", lambda self, *a, **k: object())
        with pytest.raises(RuntimeError):
            q.request_approval("r1", {"tool": "db"})
        assert failing.rolled_back is True

    def test_approve_rolls_back_on_commit_error(self, monkeypatch):
        import app.hitl.approval as approval_mod

        failing = self._failing_session()
        q = PgApprovalQueue(lambda: failing)
        from app.database.repositories.hitl_request_repository import HITLRequestRepository

        monkeypatch.setattr(HITLRequestRepository, "approve", lambda self, *a, **k: None)
        with pytest.raises(RuntimeError):
            q.approve("r1")
        assert failing.rolled_back is True

    def test_reject_rolls_back_on_commit_error(self, monkeypatch):
        failing = self._failing_session()
        q = PgApprovalQueue(lambda: failing)
        from app.database.repositories.hitl_request_repository import HITLRequestRepository

        monkeypatch.setattr(HITLRequestRepository, "reject", lambda self, *a, **k: None)
        with pytest.raises(RuntimeError):
            q.reject("r1")
        assert failing.rolled_back is True
