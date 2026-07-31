import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, text, or_, and_
from sqlalchemy.orm import Session

from app.database.models.audit_log import AuditLogModel
from app.database.repositories.base import BaseRepository

AUDIT_LOCK_KEY = 77223


def audit_content(record: "AuditLogModel") -> Dict[str, Any]:
    """Canonical, deterministic representation of an audit record for checksums."""
    return {
        "timestamp": record.timestamp.isoformat() if record.timestamp else None,
        "event_type": record.event_type,
        "status": record.status,
        "tool": record.tool,
        "action": record.action,
        "request_data": record.request_data,
        "decision": record.decision,
        "matched_rule": record.matched_rule,
        "reason": record.reason,
        "risk_level": record.risk_level,
        "correlation_id": record.correlation_id,
        "request_id": record.request_id,
        "execution_id": record.execution_id,
        "source": record.source,
        "actor": record.actor,
        "client_ip": record.client_ip,
        "user_agent": record.user_agent,
    }


def compute_checksum(content: Dict[str, Any], prev_checksum: Optional[str]) -> str:
    """SHA-256 over the canonical content chained to the previous checksum."""
    payload = json.dumps(content, sort_keys=True, default=str, separators=(",", ":"))
    chained = f"{prev_checksum or ''}:{payload}"
    return hashlib.sha256(chained.encode("utf-8")).hexdigest()


class AuditLogRepository(BaseRepository[AuditLogModel]):
    def __init__(self, session: Session):
        super().__init__(session, AuditLogModel)

    def create(
        self,
        request: Dict[str, Any],
        decision: Dict[str, Any],
        event_type: Optional[str] = None,
        status: Optional[str] = None,
        risk_level: Optional[str] = None,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        source: Optional[str] = None,
        actor: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLogModel:
        # Serialize concurrent writers so the checksum chain stays consistent.
        try:
            self.session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": AUDIT_LOCK_KEY}
            )
        except Exception:
            pass  # non-PostgreSQL dialect: rely on the transaction isolation instead

        last = (
            self.session.query(AuditLogModel)
            .order_by(AuditLogModel.id.desc())
            .first()
        )
        prev_checksum = last.checksum if last else None

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        content = {
            "timestamp": now.isoformat(),
            "event_type": event_type,
            "status": status,
            "tool": request.get("tool", ""),
            "action": request.get("action", ""),
            "request_data": request,
            "decision": decision.get("decision", ""),
            "matched_rule": decision.get("matched_rule"),
            "reason": decision.get("reason"),
            "risk_level": risk_level,
            "correlation_id": correlation_id,
            "request_id": request_id,
            "execution_id": execution_id,
            "source": source,
            "actor": actor,
            "client_ip": client_ip,
            "user_agent": user_agent,
        }
        checksum = compute_checksum(content, prev_checksum)

        model = AuditLogModel(
            timestamp=now,
            event_type=event_type,
            status=status,
            tool=content["tool"],
            action=content["action"],
            request_data=request,
            decision=content["decision"],
            matched_rule=content["matched_rule"],
            reason=content["reason"],
            risk_level=risk_level,
            correlation_id=correlation_id,
            request_id=request_id,
            execution_id=execution_id,
            source=source,
            actor=actor,
            client_ip=client_ip,
            user_agent=user_agent,
            checksum=checksum,
            prev_checksum=prev_checksum,
        )
        self.session.add(model)
        self.session.flush()
        return model

    def list_recent(self, limit: int = 50) -> List[AuditLogModel]:
        return (
            self.session.query(AuditLogModel)
            .order_by(AuditLogModel.id.desc())
            .limit(limit)
            .all()
        )

    def find_by_correlation_id(self, correlation_id: str) -> List[AuditLogModel]:
        return (
            self.session.query(AuditLogModel)
            .filter(AuditLogModel.correlation_id == correlation_id)
            .order_by(AuditLogModel.id.asc())
            .all()
        )

    # ------------------------------------------------------------------
    # Search / filtering / pagination
    # ------------------------------------------------------------------

    def _apply_filters(self, q, filters: Dict[str, Any]):
        if filters.get("tool"):
            q = q.filter(AuditLogModel.tool == filters["tool"])
        if filters.get("action"):
            q = q.filter(AuditLogModel.action == filters["action"])
        if filters.get("decision"):
            q = q.filter(AuditLogModel.decision == filters["decision"])
        if filters.get("status"):
            q = q.filter(AuditLogModel.status == filters["status"])
        if filters.get("event_type"):
            q = q.filter(AuditLogModel.event_type == filters["event_type"])
        if filters.get("risk_level"):
            q = q.filter(AuditLogModel.risk_level == filters["risk_level"])
        if filters.get("correlation_id"):
            q = q.filter(AuditLogModel.correlation_id == filters["correlation_id"])
        if filters.get("request_id"):
            q = q.filter(AuditLogModel.request_id == filters["request_id"])
        if filters.get("execution_id"):
            q = q.filter(AuditLogModel.execution_id == filters["execution_id"])
        if filters.get("source"):
            q = q.filter(AuditLogModel.source == filters["source"])
        if filters.get("actor"):
            q = q.filter(AuditLogModel.actor == filters["actor"])
        if filters.get("start_date"):
            q = q.filter(AuditLogModel.timestamp >= filters["start_date"])
        if filters.get("end_date"):
            q = q.filter(AuditLogModel.timestamp <= filters["end_date"])
        if filters.get("search"):
            like = f"%{filters['search']}%"
            q = q.filter(
                or_(
                    AuditLogModel.reason.ilike(like),
                    AuditLogModel.matched_rule.ilike(like),
                    AuditLogModel.correlation_id.ilike(like),
                    AuditLogModel.request_id.ilike(like),
                    AuditLogModel.execution_id.ilike(like),
                )
            )
        return q

    def search(
        self,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 50,
        sort_desc: bool = True,
    ) -> List[AuditLogModel]:
        q = self._apply_filters(self.session.query(AuditLogModel), filters)
        if sort_desc:
            q = q.order_by(AuditLogModel.id.desc())
        else:
            q = q.order_by(AuditLogModel.id.asc())
        return q.offset(skip).limit(limit).all()

    def count(self, filters: Dict[str, Any]) -> int:
        q = self._apply_filters(self.session.query(AuditLogModel), filters)
        return q.count()

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------

    def timeline(self, granularity: str = "hour", limit: int = 168) -> List[Dict[str, Any]]:
        dialect = self.session.bind.dialect.name if self.session.bind else "postgresql"
        if dialect == "sqlite":
            fmt = "%Y-%m-%d %H:00" if granularity == "hour" else "%Y-%m-%d"
            group_expr = func.strftime(fmt, AuditLogModel.timestamp)
        elif granularity == "day":
            group_expr = func.date_trunc("day", AuditLogModel.timestamp)
        else:
            group_expr = func.date_trunc("hour", AuditLogModel.timestamp)

        rows = (
            self.session.query(
                group_expr.label("bucket"),
                func.count().label("total"),
                AuditLogModel.decision,
            )
            .group_by(group_expr, AuditLogModel.decision)
            .order_by(group_expr.desc())
            .limit(limit)
            .all()
        )

        buckets: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            bucket = row.bucket
            key = bucket.isoformat() if hasattr(bucket, "isoformat") else str(bucket)
            entry = buckets.setdefault(
                key, {"bucket": key, "total": 0, "decisions": {}}
            )
            entry["total"] += row.total
            entry["decisions"][row.decision] = entry["decisions"].get(row.decision, 0) + row.total

        return sorted(buckets.values(), key=lambda b: b["bucket"], reverse=True)

    # ------------------------------------------------------------------
    # Integrity verification (immutability)
    # ------------------------------------------------------------------

    def verify_integrity(self, limit: Optional[int] = None) -> Dict[str, Any]:
        q = self.session.query(AuditLogModel).order_by(AuditLogModel.id.asc())
        if limit:
            q = q.limit(limit)
        records = q.all()

        errors: List[str] = []
        prev_checksum: Optional[str] = None

        for record in records:
            if record.prev_checksum != prev_checksum:
                errors.append(
                    f"Record {record.id}: chain broken (prev_checksum mismatch)"
                )
            expected = compute_checksum(audit_content(record), prev_checksum)
            if record.checksum != expected:
                errors.append(
                    f"Record {record.id}: checksum mismatch (tampered or corrupted)"
                )
            prev_checksum = record.checksum

        return {
            "valid": len(errors) == 0,
            "checked": len(records),
            "errors": errors,
        }
