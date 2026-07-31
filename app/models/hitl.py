from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ApprovalDecision(BaseModel):
    """Request body used to approve or reject a pending approval request."""

    reason: Optional[str] = Field(default=None, max_length=500, description="Optional decision reason")
    comments: Optional[str] = Field(default=None, description="Reviewer comments")


class ApprovalRequestResponse(BaseModel):
    id: int
    request_id: str
    tool: str
    action: str
    request_data: Dict[str, Any]
    policy_decision: str
    policy_reason: Optional[str] = None
    status: str
    approval_reason: Optional[str] = None
    reviewer: Optional[str] = None
    comments: Optional[str] = None
    expires_at: Optional[str] = None
    approved_at: Optional[str] = None
    rejected_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ApprovalListResult(BaseModel):
    items: List[ApprovalRequestResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ApprovalStats(BaseModel):
    total_requests: int
    pending: int
    approved: int
    rejected: int
    expired: int
    approval_rate_pct: float
    rejection_rate_pct: float
    avg_resolution_time_hours: Optional[float] = None
    by_tool: Dict[str, int]
