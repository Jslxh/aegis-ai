import csv
import io
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database.repositories.audit_log_repository import AuditLogRepository
from app.database.models.audit_log import AuditLogModel

EXPORT_CSV_COLUMNS = [
    "id",
    "timestamp",
    "event_type",
    "status",
    "tool",
    "action",
    "decision",
    "matched_rule",
    "reason",
    "risk_level",
    "correlation_id",
    "request_id",
    "execution_id",
    "source",
    "actor",
    "client_ip",
    "checksum",
]


class AuditService:
    """Enterprise audit log service: tracing, search, export and integrity."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AuditLogRepository(db)

    # ------------------------------------------------------------------
    # Tracing
    # ------------------------------------------------------------------

    @staticmethod
    def generate_correlation_id() -> str:
        return f"corr_{uuid.uuid4().hex}"

    @staticmethod
    def generate_request_id() -> str:
        return f"req_{uuid.uuid4().hex}"

    @staticmethod
    def generate_execution_id() -> str:
        return f"exec_{uuid.uuid4().hex}"

    # ------------------------------------------------------------------
    # Search / pagination
    # ------------------------------------------------------------------

    @staticmethod
    def _build_filters(
        tool: Optional[str] = None,
        action: Optional[str] = None,
        decision: Optional[str] = None,
        status: Optional[str] = None,
        event_type: Optional[str] = None,
        risk_level: Optional[str] = None,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        source: Optional[str] = None,
        actor: Optional[str] = None,
        search: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        filters: Dict[str, Any] = {}
        if tool:
            filters["tool"] = tool
        if action:
            filters["action"] = action
        if decision:
            filters["decision"] = decision
        if status:
            filters["status"] = status
        if event_type:
            filters["event_type"] = event_type
        if risk_level:
            filters["risk_level"] = risk_level
        if correlation_id:
            filters["correlation_id"] = correlation_id
        if request_id:
            filters["request_id"] = request_id
        if execution_id:
            filters["execution_id"] = execution_id
        if source:
            filters["source"] = source
        if actor:
            filters["actor"] = actor
        if search:
            filters["search"] = search
        if start_date:
            try:
                filters["start_date"] = datetime.fromisoformat(start_date)
            except ValueError:
                pass
        if end_date:
            try:
                filters["end_date"] = datetime.fromisoformat(end_date)
            except ValueError:
                pass
        return filters

    def search(
        self,
        page: int = 1,
        page_size: int = 50,
        **filters_kwargs,
    ) -> Dict[str, Any]:
        filters = self._build_filters(**filters_kwargs)
        page = max(page, 1)
        page_size = max(1, min(page_size, 500))

        total = self.repo.count(filters)
        records = self.repo.search(filters, skip=(page - 1) * page_size, limit=page_size)

        return {
            "items": [self._serialize(r) for r in records],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size if total else 0,
        }

    def timeline(self, granularity: str = "hour", limit: int = 168) -> Dict[str, Any]:
        points = self.repo.timeline(granularity=granularity, limit=limit)
        return {"granularity": granularity, "points": points}

    def by_correlation(self, correlation_id: str) -> List[Dict[str, Any]]:
        records = self.repo.find_by_correlation_id(correlation_id)
        return [self._serialize(r) for r in records]

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_csv(self, filters: Dict[str, Any], limit: int = 5000) -> str:
        records = self.repo.search(filters, skip=0, limit=limit)
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=EXPORT_CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for r in records:
            writer.writerow(self._serialize(r))
        return buffer.getvalue()

    def export_json(self, filters: Dict[str, Any], limit: int = 5000) -> List[Dict[str, Any]]:
        records = self.repo.search(filters, skip=0, limit=limit)
        return [self._serialize(r) for r in records]

    # ------------------------------------------------------------------
    # Integrity
    # ------------------------------------------------------------------

    def verify_integrity(self, limit: Optional[int] = None) -> Dict[str, Any]:
        return self.repo.verify_integrity(limit=limit)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize(r: AuditLogModel) -> Dict[str, Any]:
        return {
            "id": r.id,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "event_type": r.event_type,
            "status": r.status,
            "tool": r.tool,
            "action": r.action,
            "request_data": r.request_data,
            "decision": r.decision,
            "matched_rule": r.matched_rule,
            "reason": r.reason,
            "risk_level": r.risk_level,
            "correlation_id": r.correlation_id,
            "request_id": r.request_id,
            "execution_id": r.execution_id,
            "source": r.source,
            "actor": r.actor,
            "client_ip": r.client_ip,
            "user_agent": r.user_agent,
            "checksum": r.checksum,
            "prev_checksum": r.prev_checksum,
        }
