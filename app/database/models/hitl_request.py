from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, func
from app.database.session import Base


class HITLRequestModel(Base):
    __tablename__ = "hitl_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(255), unique=True, nullable=False, index=True)
    tool = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    request_data = Column(JSON, nullable=False)
    policy_decision = Column(String(50), nullable=False)
    policy_reason = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    approval_reason = Column(String(500), nullable=True)
    reviewer = Column(String(255), nullable=True)
    comments = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self) -> dict:
        def _iso(value):
            return value.isoformat() if value else None

        return {
            "id": self.id,
            "request_id": self.request_id,
            "tool": self.tool,
            "action": self.action,
            "request_data": self.request_data,
            "policy_decision": self.policy_decision,
            "policy_reason": self.policy_reason,
            "status": self.status,
            "approval_reason": self.approval_reason,
            "reviewer": self.reviewer,
            "comments": self.comments,
            "expires_at": _iso(self.expires_at),
            "approved_at": _iso(self.approved_at),
            "rejected_at": _iso(self.rejected_at),
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }
