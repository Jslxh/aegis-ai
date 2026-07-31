from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session


class BaseApprovalQueue(ABC):
    """Abstract interface to decouple action guardrails from specific human-in-the-loop systems."""

    @abstractmethod
    def request_approval(self, request_id: str, action_data: Dict[str, Any], decision: str = "", reason: str = "") -> bool:
        """Submits a task for human approval. Returns True if approved immediately."""
        pass

    @abstractmethod
    def approve(self, request_id: str, reason: Optional[str] = None) -> None:
        """Approves a pending request by ID."""
        pass

    @abstractmethod
    def reject(self, request_id: str, reason: Optional[str] = None) -> None:
        """Rejects a pending request by ID with a reason."""
        pass

    @abstractmethod
    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Retrieves a list of all current pending requests."""
        pass


class MockApprovalQueue(BaseApprovalQueue):
    """Default implementation tracking approvals in-memory."""

    def __init__(self):
        self.pending = {}

    def request_approval(self, request_id: str, action_data: Dict[str, Any], decision: str = "", reason: str = "") -> bool:
        self.pending[request_id] = action_data
        return False

    def approve(self, request_id: str, reason: Optional[str] = None) -> None:
        if request_id in self.pending:
            del self.pending[request_id]

    def reject(self, request_id: str, reason: Optional[str] = None) -> None:
        if request_id in self.pending:
            del self.pending[request_id]

    def get_pending_requests(self) -> List[Dict[str, Any]]:
        return list(self.pending.values())


class PgApprovalQueue(BaseApprovalQueue):
    """PostgreSQL-backed approval queue using the repository pattern."""

    def __init__(self, session_factory: callable):
        self.session_factory = session_factory

    def request_approval(
        self,
        request_id: str,
        action_data: Dict[str, Any],
        decision: str = "",
        reason: str = "",
        expires_at: Optional[datetime] = None,
    ) -> bool:
        """Submits a task for human approval. Returns True if approved immediately."""
        from app.database.repositories.hitl_request_repository import HITLRequestRepository

        session: Session = self.session_factory()
        try:
            repo = HITLRequestRepository(session)
            repo.create_request(request_id, action_data, decision, reason, expires_at=expires_at)
            session.commit()
            return False
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def approve(self, request_id: str, reason: Optional[str] = None,
                reviewer: Optional[str] = None, comments: Optional[str] = None) -> None:
        from app.database.repositories.hitl_request_repository import HITLRequestRepository

        session: Session = self.session_factory()
        try:
            repo = HITLRequestRepository(session)
            repo.approve(request_id, reason, reviewer=reviewer, comments=comments)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def reject(self, request_id: str, reason: Optional[str] = None,
               reviewer: Optional[str] = None, comments: Optional[str] = None) -> None:
        from app.database.repositories.hitl_request_repository import HITLRequestRepository

        session: Session = self.session_factory()
        try:
            repo = HITLRequestRepository(session)
            repo.reject(request_id, reason, reviewer=reviewer, comments=comments)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_pending_requests(self) -> List[Dict[str, Any]]:
        from app.database.repositories.hitl_request_repository import HITLRequestRepository

        session: Session = self.session_factory()
        try:
            repo = HITLRequestRepository(session)
            models = repo.list_pending()
            return [m.to_dict() for m in models]
        finally:
            session.close()
