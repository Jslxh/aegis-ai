from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseApprovalQueue(ABC):
    """Abstract interface to decouple action guardrails from specific human-in-the-loop systems."""

    @abstractmethod
    def request_approval(self, request_id: str, action_data: Dict[str, Any]) -> bool:
        """Submits a task for human approval. Returns True if approved immediately."""
        pass

    @abstractmethod
    def approve(self, request_id: str) -> None:
        """Approves a pending request by ID."""
        pass

    @abstractmethod
    def reject(self, request_id: str, reason: str) -> None:
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

    def request_approval(self, request_id: str, action_data: Dict[str, Any]) -> bool:
        self.pending[request_id] = action_data
        return False

    def approve(self, request_id: str) -> None:
        if request_id in self.pending:
            del self.pending[request_id]

    def reject(self, request_id: str, reason: str) -> None:
        if request_id in self.pending:
            del self.pending[request_id]

    def get_pending_requests(self) -> List[Dict[str, Any]]:
        return list(self.pending.values())
