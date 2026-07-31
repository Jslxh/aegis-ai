from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, case, and_
from sqlalchemy.orm import Session

from app.database.models.runtime_metric import RuntimeMetricModel
from app.database.models.hitl_request import HITLRequestModel
from app.database.models.analytics_report import AnalyticsReportModel
from app.database.repositories.base import BaseRepository


class AnalyticsRepository(BaseRepository[AnalyticsReportModel]):
    def __init__(self, session: Session):
        super().__init__(session, AnalyticsReportModel)

    # ------------------------------------------------------------------
    # Policy Effectiveness
    # ------------------------------------------------------------------

    def policy_effectiveness(self, since: Optional[datetime] = None, limit: int = 20) -> List[Dict[str, Any]]:
        filters = [RuntimeMetricModel.matched_rule.isnot(None)]
        if since:
            filters.append(RuntimeMetricModel.timestamp >= since)

        blocked_case = case((RuntimeMetricModel.decision == "block", 1), else_=0)
        hitl_case = case((RuntimeMetricModel.decision == "require_hitl", 1), else_=0)

        rows = (
            self.session.query(
                RuntimeMetricModel.matched_rule.label("rule_id"),
                func.count().label("total_matches"),
                func.sum(blocked_case).label("blocked_count"),
                func.sum(hitl_case).label("hitl_count"),
            )
            .filter(*filters)
            .group_by(RuntimeMetricModel.matched_rule)
            .order_by(func.count().desc())
            .limit(limit)
            .all()
        )

        result = []
        for r in rows:
            total = r.total_matches
            blocked = r.blocked_count or 0
            hitl = r.hitl_count or 0
            allowed = total - blocked - hitl
            result.append({
                "rule_id": r.rule_id,
                "total_matches": total,
                "blocked_count": blocked,
                "allowed_count": allowed,
                "hitl_count": hitl,
                "effectiveness_pct": round((allowed / total) * 100, 2) if total else 0.0,
            })
        return result

    # ------------------------------------------------------------------
    # Most Triggered Rules
    # ------------------------------------------------------------------

    def most_triggered_rules(self, since: Optional[datetime] = None, limit: int = 10) -> List[Dict[str, Any]]:
        filters = [RuntimeMetricModel.matched_rule.isnot(None)]
        if since:
            filters.append(RuntimeMetricModel.timestamp >= since)

        blocked_case = case((RuntimeMetricModel.decision == "block", 1), else_=0)

        rows = (
            self.session.query(
                RuntimeMetricModel.matched_rule.label("rule_id"),
                func.count().label("trigger_count"),
                func.sum(blocked_case).label("blocked_count"),
                func.count(func.distinct(RuntimeMetricModel.tool)).label("tools_affected"),
            )
            .filter(*filters)
            .group_by(RuntimeMetricModel.matched_rule)
            .order_by(func.count().desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "rule_id": r.rule_id,
                "trigger_count": r.trigger_count,
                "blocked_count": r.blocked_count or 0,
                "tools_affected": r.tools_affected,
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Most Dangerous Tools
    # ------------------------------------------------------------------

    def most_dangerous_tools(self, since: Optional[datetime] = None, limit: int = 10) -> List[Dict[str, Any]]:
        filters = []
        if since:
            filters.append(RuntimeMetricModel.timestamp >= since)

        blocked_case = case((RuntimeMetricModel.decision == "block", 1), else_=0)
        failure_case = case((RuntimeMetricModel.execution_status == "failed", 1), else_=0)
        hitl_case = case((RuntimeMetricModel.decision == "require_hitl", 1), else_=0)

        rows = (
            self.session.query(
                RuntimeMetricModel.tool,
                func.count().label("total_requests"),
                func.sum(blocked_case).label("blocked_count"),
                func.sum(failure_case).label("failure_count"),
                func.sum(hitl_case).label("hitl_count"),
                func.avg(RuntimeMetricModel.execution_time_ms).label("avg_latency_ms"),
            )
            .filter(*filters)
            .group_by(RuntimeMetricModel.tool)
            .order_by(func.count().desc())
            .limit(limit)
            .all()
        )

        result = []
        for r in rows:
            total = r.total_requests
            blocked = r.blocked_count or 0
            result.append({
                "tool": r.tool,
                "total_requests": total,
                "blocked_count": blocked,
                "failure_count": r.failure_count or 0,
                "hitl_count": r.hitl_count or 0,
                "avg_latency_ms": round(r.avg_latency_ms, 2) if r.avg_latency_ms else 0.0,
                "block_rate_pct": round((blocked / total) * 100, 2) if total else 0.0,
            })
        # Sort by block rate descending so the most dangerous tools lead
        result.sort(key=lambda x: (x["block_rate_pct"], x["total_requests"]), reverse=True)
        return result

    # ------------------------------------------------------------------
    # Blocked Requests
    # ------------------------------------------------------------------

    def blocked_requests(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        filters = []
        if since:
            filters.append(RuntimeMetricModel.timestamp >= since)

        total = self.session.query(func.count()).filter(*filters).scalar() or 0
        blocked = (
            self.session.query(func.count())
            .filter(*filters, RuntimeMetricModel.decision == "block")
            .scalar()
            or 0
        )

        day_expr = func.date_trunc("day", RuntimeMetricModel.timestamp)
        breakdown_rows = (
            self.session.query(
                day_expr.label("day"),
                func.sum(case((RuntimeMetricModel.decision == "block", 1), else_=0)).label("blocked"),
                func.count().label("total"),
            )
            .filter(*filters)
            .group_by(day_expr)
            .order_by(day_expr)
            .all()
        )

        breakdown = []
        for r in breakdown_rows:
            day = r.day
            day_str = day.isoformat() if hasattr(day, "isoformat") else str(day)
            breakdown.append({
                "day": day_str,
                "blocked": r.blocked or 0,
                "total": r.total,
            })

        return {
            "total_blocked": blocked,
            "total_requests": total,
            "block_rate_pct": round((blocked / total) * 100, 2) if total else 0.0,
            "breakdown": breakdown,
        }

    # ------------------------------------------------------------------
    # HITL Statistics
    # ------------------------------------------------------------------

    def hitl_statistics(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        filters = []
        if since:
            filters.append(HITLRequestModel.created_at >= since)

        rows = (
            self.session.query(HITLRequestModel.status, func.count().label("count"))
            .filter(*filters)
            .group_by(HITLRequestModel.status)
            .all()
        )

        counts = {r.status: r.count for r in rows}
        total = sum(counts.values())
        pending = counts.get("pending", 0)
        approved = counts.get("approved", 0)
        rejected = counts.get("rejected", 0)

        # Avg approval time: time from created_at to updated_at for approved/rejected
        resolution = (
            self.session.query(func.avg(func.extract("epoch", HITLRequestModel.updated_at - HITLRequestModel.created_at) / 3600.0))
            .filter(*filters, HITLRequestModel.status.in_(["approved", "rejected"]))
            .scalar()
        )

        approval = (
            self.session.query(func.avg(func.extract("epoch", HITLRequestModel.updated_at - HITLRequestModel.created_at) / 3600.0))
            .filter(*filters, HITLRequestModel.status == "approved")
            .scalar()
        )

        by_tool_rows = (
            self.session.query(HITLRequestModel.tool, func.count().label("count"))
            .filter(*filters)
            .group_by(HITLRequestModel.tool)
            .order_by(func.count().desc())
            .all()
        )

        return {
            "total_requests": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "approval_rate_pct": round((approved / total) * 100, 2) if total else 0.0,
            "rejection_rate_pct": round((rejected / total) * 100, 2) if total else 0.0,
            "avg_approval_time_hours": round(approval, 2) if approval is not None else None,
            "avg_resolution_time_hours": round(resolution, 2) if resolution is not None else None,
            "by_tool": {r.tool: r.count for r in by_tool_rows},
        }

    # ------------------------------------------------------------------
    # Response Time
    # ------------------------------------------------------------------

    def avg_response_time(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        filters = []
        if since:
            filters.append(RuntimeMetricModel.timestamp >= since)

        row = (
            self.session.query(
                func.avg(RuntimeMetricModel.execution_time_ms).label("avg_time"),
                func.min(RuntimeMetricModel.execution_time_ms).label("min_time"),
                func.max(RuntimeMetricModel.execution_time_ms).label("max_time"),
                func.avg(RuntimeMetricModel.tool_latency_ms).label("avg_tool_latency"),
                func.count().label("total_requests"),
            )
            .filter(*filters)
            .one()
        )

        median = (
            self.session.query(
                func.percentile_cont(0.5).within_group(RuntimeMetricModel.execution_time_ms)
            )
            .filter(*filters)
            .scalar()
        )

        by_tool_rows = (
            self.session.query(
                RuntimeMetricModel.tool,
                func.avg(RuntimeMetricModel.execution_time_ms).label("avg_time_ms"),
                func.min(RuntimeMetricModel.execution_time_ms).label("min_time_ms"),
                func.max(RuntimeMetricModel.execution_time_ms).label("max_time_ms"),
                func.count().label("requests"),
            )
            .filter(*filters)
            .group_by(RuntimeMetricModel.tool)
            .order_by(func.avg(RuntimeMetricModel.execution_time_ms).desc())
            .all()
        )

        return {
            "avg_execution_time_ms": round(row.avg_time, 2) if row.avg_time else 0.0,
            "min_execution_time_ms": round(row.min_time, 2) if row.min_time else 0.0,
            "max_execution_time_ms": round(row.max_time, 2) if row.max_time else 0.0,
            "median_execution_time_ms": round(median, 2) if median is not None else 0.0,
            "avg_tool_latency_ms": round(row.avg_tool_latency, 2) if row.avg_tool_latency else None,
            "total_requests": row.total_requests,
            "by_tool": [
                {
                    "tool": r.tool,
                    "avg_time_ms": round(r.avg_time_ms, 2) if r.avg_time_ms else 0.0,
                    "min_time_ms": round(r.min_time_ms, 2) if r.min_time_ms else 0.0,
                    "max_time_ms": round(r.max_time_ms, 2) if r.max_time_ms else 0.0,
                    "requests": r.requests,
                }
                for r in by_tool_rows
            ],
        }

    # ------------------------------------------------------------------
    # Risk Distribution
    # ------------------------------------------------------------------

    def risk_distribution(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        filters = []
        if since:
            filters.append(RuntimeMetricModel.timestamp >= since)

        rows = (
            self.session.query(
                RuntimeMetricModel.risk_level,
                func.count().label("count"),
            )
            .filter(*filters)
            .group_by(RuntimeMetricModel.risk_level)
            .order_by(func.count().desc())
            .all()
        )

        total = sum(r.count for r in rows)
        return {
            "items": [
                {
                    "risk_level": r.risk_level,
                    "count": r.count,
                    "percentage": round((r.count / total) * 100, 2) if total else 0.0,
                }
                for r in rows
            ],
            "total": total,
        }

    # ------------------------------------------------------------------
    # Reports (persisted)
    # ------------------------------------------------------------------

    def find_report(self, report_type: str, period: str) -> Optional[AnalyticsReportModel]:
        return (
            self.session.query(AnalyticsReportModel)
            .filter(
                AnalyticsReportModel.report_type == report_type,
                AnalyticsReportModel.period == period,
            )
            .order_by(AnalyticsReportModel.generated_at.desc())
            .first()
        )

    def list_reports(self, report_type: Optional[str] = None, limit: int = 50) -> List[AnalyticsReportModel]:
        q = self.session.query(AnalyticsReportModel)
        if report_type:
            q = q.filter(AnalyticsReportModel.report_type == report_type)
        return q.order_by(AnalyticsReportModel.generated_at.desc()).limit(limit).all()

    def upsert_report(self, report_type: str, period: str, data: Dict[str, Any]) -> AnalyticsReportModel:
        model = self.find_report(report_type, period)
        if model:
            model.data = data
            model.generated_at = func.now()
            self.session.flush()
            return model
        model = AnalyticsReportModel(
            report_type=report_type,
            period=period,
            data=data,
        )
        return self.add(model)
