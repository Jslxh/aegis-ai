from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database.models.hitl_request import HITLRequestModel
from app.database.repositories.base import BaseRepository

HITL_RESOLVABLE_STATUSES = ("pending",)


class HITLRequestRepository(BaseRepository[HITLRequestModel]):
    def __init__(self, session: Session):
        super().__init__(session, HITLRequestModel)

    def create_request(
        self,
        request_id: str,
        request_data: Dict[str, Any],
        decision: str,
        reason: str | None,
        expires_at: Optional[datetime] = None,
    ) -> HITLRequestModel:
        model = HITLRequestModel(
            request_id=request_id,
            tool=request_data.get("tool", ""),
            action=request_data.get("action", ""),
            request_data=request_data,
            policy_decision=decision,
            policy_reason=reason,
            status="pending",
            expires_at=expires_at,
        )
        return self.add(model)

    def find_by_request_id(self, request_id: str) -> HITLRequestModel | None:
        return (
            self.session.query(HITLRequestModel)
            .filter(HITLRequestModel.request_id == request_id)
            .first()
        )

    def get_by_id(self, approval_id: int) -> HITLRequestModel | None:
        return self.session.get(HITLRequestModel, approval_id)

    # ------------------------------------------------------------------
    # Listing / filtering / pagination
    # ------------------------------------------------------------------

    def _apply_filters(self, q, status: Optional[str] = None, tool: Optional[str] = None):
        if status:
            q = q.filter(HITLRequestModel.status == status)
        if tool:
            q = q.filter(HITLRequestModel.tool == tool)
        return q

    def list_requests(
        self,
        status: Optional[str] = None,
        tool: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[HITLRequestModel]:
        q = self._apply_filters(
            self.session.query(HITLRequestModel), status=status, tool=tool
        )
        return q.order_by(HITLRequestModel.created_at.desc()).offset(skip).limit(limit).all()

    def list_pending(self) -> List[HITLRequestModel]:
        return (
            self.session.query(HITLRequestModel)
            .filter(HITLRequestModel.status == "pending")
            .order_by(HITLRequestModel.created_at.desc())
            .all()
        )

    def count_requests(self, status: Optional[str] = None, tool: Optional[str] = None) -> int:
        q = self._apply_filters(
            self.session.query(HITLRequestModel), status=status, tool=tool
        )
        return q.count()

    # ------------------------------------------------------------------
    # Workflow transitions
    # ------------------------------------------------------------------

    def approve(
        self,
        request_id: str,
        reason: str | None = None,
        reviewer: Optional[str] = None,
        comments: Optional[str] = None,
    ) -> HITLRequestModel | None:
        model = self.find_by_request_id(request_id)
        if model and model.status in HITL_RESOLVABLE_STATUSES:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            model.status = "approved"
            model.approval_reason = reason
            model.reviewer = reviewer
            model.comments = comments
            model.approved_at = now
            self.session.flush()
        return model

    def reject(
        self,
        request_id: str,
        reason: str | None = None,
        reviewer: Optional[str] = None,
        comments: Optional[str] = None,
    ) -> HITLRequestModel | None:
        model = self.find_by_request_id(request_id)
        if model and model.status in HITL_RESOLVABLE_STATUSES:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            model.status = "rejected"
            model.approval_reason = reason
            model.reviewer = reviewer
            model.comments = comments
            model.rejected_at = now
            self.session.flush()
        return model

    def expire(self, request_id: str) -> HITLRequestModel | None:
        """Auto-expire a pending request that exceeded its deadline."""
        model = self.find_by_request_id(request_id)
        if model and model.status == "pending":
            model.status = "expired"
            self.session.flush()
        return model

    def expire_stale(self, now: Optional[datetime] = None) -> int:
        """Expire all pending requests past their expires_at deadline."""
        now = now or datetime.now(timezone.utc).replace(tzinfo=None)
        rows = (
            self.session.query(HITLRequestModel)
            .filter(
                HITLRequestModel.status == "pending",
                HITLRequestModel.expires_at.isnot(None),
                HITLRequestModel.expires_at < now,
            )
            .all()
        )
        for row in rows:
            row.status = "expired"
        self.session.flush()
        return len(rows)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        rows = (
            self.session.query(HITLRequestModel.status, func.count())
            .group_by(HITLRequestModel.status)
            .all()
        )
        status_counts = {status: count for status, count in rows}
        total = sum(status_counts.values())

        resolved_at = func.coalesce(
            HITLRequestModel.approved_at, HITLRequestModel.rejected_at
        )
        by_tool_rows = (
            self.session.query(HITLRequestModel.tool, func.count())
            .group_by(HITLRequestModel.tool)
            .all()
        )

        avg_resolution: Optional[float] = None
        if total:
            dialect = self.session.bind.dialect.name if self.session.bind else "postgresql"
            if dialect == "sqlite":
                seconds_expr = func.strftime("%s", resolved_at) - func.strftime(
                    "%s", HITLRequestModel.created_at
                )
            else:
                seconds_expr = (
                    func.extract("epoch", resolved_at)
                    - func.extract("epoch", HITLRequestModel.created_at)
                )
            avg_row = self.session.query(func.avg(seconds_expr)).filter(
                resolved_at.isnot(None)
            ).first()
            if avg_row and avg_row[0] is not None:
                avg_resolution = round(float(avg_row[0]) / 3600.0, 2)

        approved = status_counts.get("approved", 0)
        rejected = status_counts.get("rejected", 0)
        return {
            "total_requests": total,
            "pending": status_counts.get("pending", 0),
            "approved": approved,
            "rejected": rejected,
            "expired": status_counts.get("expired", 0),
            "approval_rate_pct": round((approved / total * 100), 1) if total else 0.0,
            "rejection_rate_pct": round((rejected / total * 100), 1) if total else 0.0,
            "avg_resolution_time_hours": avg_resolution,
            "by_tool": dict(by_tool_rows),
        }
