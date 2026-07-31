"""Unit tests for the HITL approval queue (in-memory mock + abstract base)."""

import pytest

from app.hitl.approval import BaseApprovalQueue, MockApprovalQueue


class _ConcreteQueue(BaseApprovalQueue):
    def request_approval(self, request_id, action_data, decision="", reason=""):
        return super().request_approval(request_id, action_data, decision, reason)

    def approve(self, request_id, reason=None):
        super().approve(request_id, reason)

    def reject(self, request_id, reason=None):
        super().reject(request_id, reason)

    def get_pending_requests(self):
        return super().get_pending_requests()


@pytest.mark.unit
class TestBaseApprovalQueue:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseApprovalQueue()

    def test_abstract_methods_are_noops(self):
        q = _ConcreteQueue()
        assert q.request_approval("r1", {"tool": "db"}, "block") is None
        assert q.get_pending_requests() is None
        q.approve("r1")
        q.reject("r1")


@pytest.mark.unit
class TestMockApprovalQueue:
    def test_request_returns_false_and_tracks(self):
        q = MockApprovalQueue()
        assert q.request_approval("r1", {"tool": "database"}, "block", "too risky") is False
        assert q.get_pending_requests() == [{"tool": "database"}]

    def test_approve_removes_pending(self):
        q = MockApprovalQueue()
        q.request_approval("r1", {"tool": "database"})
        q.approve("r1", "looks fine")
        assert q.get_pending_requests() == []

    def test_reject_removes_pending(self):
        q = MockApprovalQueue()
        q.request_approval("r1", {"tool": "database"})
        q.reject("r1", "nope")
        assert q.get_pending_requests() == []

    def test_approve_missing_id_is_noop(self):
        q = MockApprovalQueue()
        q.request_approval("r1", {"tool": "database"})
        q.approve("does-not-exist")
        assert q.get_pending_requests() == [{"tool": "database"}]

    def test_reject_missing_id_is_noop(self):
        q = MockApprovalQueue()
        q.request_approval("r1", {"tool": "database"})
        q.reject("does-not-exist")
        assert len(q.get_pending_requests()) == 1

    def test_multiple_pending(self):
        q = MockApprovalQueue()
        q.request_approval("r1", {"tool": "email"})
        q.request_approval("r2", {"tool": "file"})
        assert len(q.get_pending_requests()) == 2
