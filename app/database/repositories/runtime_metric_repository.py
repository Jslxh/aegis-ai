from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func, cast, Date, case
from sqlalchemy.orm import Session

from app.database.models.runtime_metric import RuntimeMetricModel
from app.database.repositories.base import BaseRepository


class RuntimeMetricRepository(BaseRepository[RuntimeMetricModel]):
    def __init__(self, session: Session):
        super().__init__(session, RuntimeMetricModel)

    def create_metric(
        self,
        tool: str,
        action: str,
        decision: str,
        execution_status: str,
        risk_level: str,
        execution_time_ms: float,
        matched_rule: Optional[str] = None,
        reason: Optional[str] = None,
        tool_latency_ms: Optional[float] = None,
        request_data: Optional[Dict[str, Any]] = None,
        tool_output: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
        execution_id: Optional[str] = None,
    ) -> RuntimeMetricModel:
        model = RuntimeMetricModel(
            tool=tool,
            action=action,
            decision=decision,
            matched_rule=matched_rule,
            reason=reason,
            execution_time_ms=execution_time_ms,
            tool_latency_ms=tool_latency_ms,
            execution_status=execution_status,
            risk_level=risk_level,
            request_data=request_data,
            tool_output=tool_output,
            user_id=user_id,
            correlation_id=correlation_id,
            request_id=request_id,
            execution_id=execution_id,
        )
        return self.add(model)

    def summary(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        q = self.session.query(RuntimeMetricModel)
        if since:
            q = q.filter(RuntimeMetricModel.timestamp >= since)

        total = q.count()
        if total == 0:
            return {
                "total_requests": 0,
                "blocked_count": 0,
                "allowed_count": 0,
                "hitl_count": 0,
                "log_and_allow_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "avg_execution_time_ms": 0.0,
                "avg_tool_latency_ms": None,
            }

        blocked = q.filter(RuntimeMetricModel.decision == "block").count()
        allowed = q.filter(RuntimeMetricModel.decision == "allow").count()
        log_and_allow = q.filter(RuntimeMetricModel.decision == "log_and_allow").count()
        hitl = q.filter(RuntimeMetricModel.decision == "require_hitl").count()

        success = q.filter(RuntimeMetricModel.execution_status == "executed").count()
        failure = q.filter(RuntimeMetricModel.execution_status == "failed").count()

        base_q = self.session.query(RuntimeMetricModel)
        if since:
            base_q = base_q.filter(RuntimeMetricModel.timestamp >= since)

        avg_time = base_q.with_entities(
            func.avg(RuntimeMetricModel.execution_time_ms)
        ).scalar() or 0.0

        avg_latency = base_q.filter(
            RuntimeMetricModel.tool_latency_ms.isnot(None)
        ).with_entities(
            func.avg(RuntimeMetricModel.tool_latency_ms)
        ).scalar()

        return {
            "total_requests": total,
            "blocked_count": blocked,
            "allowed_count": allowed,
            "hitl_count": hitl,
            "log_and_allow_count": log_and_allow,
            "success_count": success,
            "failure_count": failure,
            "avg_execution_time_ms": float(avg_time),
            "avg_tool_latency_ms": float(avg_latency) if avg_latency else None,
        }

    def timeline(
        self,
        since: datetime,
        granularity: str = "hour",
    ) -> List[Dict[str, Any]]:
        if granularity == "hour":
            group_expr = func.date_trunc("hour", RuntimeMetricModel.timestamp)
        elif granularity == "day":
            group_expr = cast(RuntimeMetricModel.timestamp, Date)
        else:
            group_expr = func.date_trunc("hour", RuntimeMetricModel.timestamp)

        blocked_case = case(
            (RuntimeMetricModel.decision == "block", 1),
            else_=0,
        )
        failed_case = case(
            (RuntimeMetricModel.execution_status == "failed", 1),
            else_=0,
        )
 
        rows = (
            self.session.query(
                group_expr.label("bucket"),
                func.count().label("total"),
                func.sum(blocked_case).label("blocked"),
                func.sum(failed_case).label("failed"),
            )
            .filter(RuntimeMetricModel.timestamp >= since)
            .group_by(group_expr)
            .order_by(group_expr)
            .all()
        )
 
        result = []
        for row in rows:
            bucket = row.bucket
            if hasattr(bucket, "isoformat"):
                bucket_str = bucket.isoformat()
            else:
                bucket_str = str(bucket)
            result.append({
                "timestamp": bucket_str,
                "total": row.total,
                "blocked": row.blocked,
                "allowed": row.total - row.blocked,
                "failed": int(row.failed or 0),
            })
        return result

    def recent_activity(
        self, limit: int = 50, since: Optional[datetime] = None
    ) -> List[RuntimeMetricModel]:
        q = self.session.query(RuntimeMetricModel)
        if since:
            q = q.filter(RuntimeMetricModel.timestamp >= since)
        return (
            q.order_by(RuntimeMetricModel.timestamp.desc())
            .limit(limit)
            .all()
        )

    def top_violations(
        self, limit: int = 10, since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        q = (
            self.session.query(
                RuntimeMetricModel.matched_rule,
                func.count().label("count"),
                func.max(RuntimeMetricModel.timestamp).label("last_occurrence"),
                RuntimeMetricModel.tool,
                RuntimeMetricModel.action,
            )
            .filter(
                RuntimeMetricModel.matched_rule.isnot(None),
                RuntimeMetricModel.decision == "block",
            )
        )

        if since:
            q = q.filter(RuntimeMetricModel.timestamp >= since)

        rows = (
            q.group_by(
                RuntimeMetricModel.matched_rule,
                RuntimeMetricModel.tool,
                RuntimeMetricModel.action,
            )
            .order_by(func.count().desc())
            .limit(limit)
            .all()
        )

        result = []
        for row in rows:
            last_occ = row.last_occurrence
            if hasattr(last_occ, "isoformat"):
                last_str = last_occ.isoformat()
            else:
                last_str = str(last_occ)
            result.append({
                "matched_rule": row.matched_rule,
                "count": row.count,
                "last_occurrence": last_str,
                "tool": row.tool,
                "action": row.action,
            })
        return result
