from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database.session import get_db_optional
from app.database.repositories.runtime_metric_repository import RuntimeMetricRepository
from app.database.repositories.policy_repository import PolicyRepository
from app.auth.dependencies import require_role, optional_require_role
from app.models.monitoring import (
    MetricSummary,
    MetricTimeline,
    TimelinePoint,
    RecentActivityItem,
    ViolationItem,
    DashboardStats,
    RuntimeMetricResponse,
)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


def _parse_time_range(time_range: str) -> Optional[datetime]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if time_range == "1h":
        return now - timedelta(hours=1)
    elif time_range == "24h":
        return now - timedelta(hours=24)
    elif time_range == "7d":
        return now - timedelta(days=7)
    elif time_range == "30d":
        return now - timedelta(days=30)
    elif time_range == "all":
        return None
    return now - timedelta(hours=24)


def _risk_level(decision: str, execution_status: str) -> str:
    if execution_status == "failed":
        return "high"
    if decision == "block":
        return "critical"
    if decision == "require_hitl":
        return "high"
    if decision == "log_and_allow":
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Runtime Metrics API
# ---------------------------------------------------------------------------


@router.get("/metrics", response_model=MetricSummary)
def get_metrics(
    time_range: str = Query("24h", description="Time range: 1h, 24h, 7d, 30d, all"),
    _: dict = Depends(require_role("viewer")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        since = _parse_time_range(time_range)
        repo = RuntimeMetricRepository(db)
        return MetricSummary(**repo.summary(since))
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/metrics/timeline", response_model=MetricTimeline)
def get_metrics_timeline(
    time_range: str = Query("24h", description="Time range: 1h, 24h, 7d, 30d, all"),
    granularity: str = Query("hour", description="Granularity: hour, day"),
    _: dict = Depends(require_role("viewer")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        since = _parse_time_range(time_range)
        if not since:
            since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
        repo = RuntimeMetricRepository(db)
        points_data = repo.timeline(since, granularity)
        points = [TimelinePoint(**p) for p in points_data]
        return MetricTimeline(granularity=granularity, points=points)
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


# ---------------------------------------------------------------------------
# Dashboard API
# ---------------------------------------------------------------------------


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(
    _: dict = Depends(require_role("viewer")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        repo = RuntimeMetricRepository(db)
        since_24h = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
        summary = repo.summary(since_24h)

        total = summary["total_requests"]
        blocked = summary["blocked_count"]
        success_rate = (summary["success_count"] / total * 100) if total > 0 else 0.0

        risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        recent = repo.recent_activity(limit=50, since=since_24h)
        for m in recent:
            rl = m.risk_level if hasattr(m, "risk_level") else _risk_level(m.decision, m.execution_status)
            if rl in risk_counts:
                risk_counts[rl] += 1
        top_risk = max(risk_counts, key=risk_counts.get) if total > 0 else "low"

        policy_repo = PolicyRepository(db)
        active_rules = policy_repo.list_all(enabled_only=True)
        active_count = len(active_rules)

        activity_items = []
        for m in recent[:10]:
            ts = m.timestamp
            if hasattr(ts, "isoformat"):
                ts_str = ts.isoformat()
            else:
                ts_str = str(ts)
            rl = m.risk_level if hasattr(m, "risk_level") else _risk_level(m.decision, m.execution_status)
            activity_items.append(
                RecentActivityItem(
                    id=m.id,
                    timestamp=ts_str,
                    tool=m.tool,
                    action=m.action,
                    decision=m.decision,
                    matched_rule=m.matched_rule,
                    execution_status=m.execution_status,
                    execution_time_ms=m.execution_time_ms,
                    risk_level=rl,
                )
            )

        return DashboardStats(
            total_requests=summary["total_requests"],
            blocked_count=blocked,
            success_rate=round(success_rate, 1),
            avg_execution_time_ms=round(summary["avg_execution_time_ms"], 2),
            active_rules_count=active_count,
            top_risk_level=top_risk,
            recent_activity=activity_items,
        )
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


# ---------------------------------------------------------------------------
# Recent Activity API
# ---------------------------------------------------------------------------


@router.get("/activity", response_model=list[RecentActivityItem])
def get_recent_activity(
    limit: int = Query(50, ge=1, le=500),
    time_range: str = Query("24h", description="Time range: 1h, 24h, 7d, 30d, all"),
    _: dict = Depends(require_role("viewer")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        since = _parse_time_range(time_range)
        repo = RuntimeMetricRepository(db)
        records = repo.recent_activity(limit=limit, since=since)
        items = []
        for m in records:
            ts = m.timestamp
            if hasattr(ts, "isoformat"):
                ts_str = ts.isoformat()
            else:
                ts_str = str(ts)
            rl = m.risk_level if hasattr(m, "risk_level") else _risk_level(m.decision, m.execution_status)
            items.append(
                RecentActivityItem(
                    id=m.id,
                    timestamp=ts_str,
                    tool=m.tool,
                    action=m.action,
                    decision=m.decision,
                    matched_rule=m.matched_rule,
                    execution_status=m.execution_status,
                    execution_time_ms=m.execution_time_ms,
                    risk_level=rl,
                )
            )
        return items
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


# ---------------------------------------------------------------------------
# Top Violations API
# ---------------------------------------------------------------------------


@router.get("/violations/top", response_model=list[ViolationItem])
def get_top_violations(
    limit: int = Query(10, ge=1, le=100),
    time_range: str = Query("24h", description="Time range: 1h, 24h, 7d, 30d, all"),
    _: dict = Depends(require_role("viewer")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        since = _parse_time_range(time_range)
        repo = RuntimeMetricRepository(db)
        rows = repo.top_violations(limit=limit, since=since)
        return [ViolationItem(**r) for r in rows]
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


# ---------------------------------------------------------------------------
# Raw Metrics Access
# ---------------------------------------------------------------------------


@router.get("/metrics/raw", response_model=list[RuntimeMetricResponse])
def get_raw_metrics(
    limit: int = Query(100, ge=1, le=1000),
    time_range: str = Query("24h", description="Time range: 1h, 24h, 7d, 30d, all"),
    decision: Optional[str] = Query(None, description="Filter by decision"),
    _: dict = Depends(require_role("auditor")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        since = _parse_time_range(time_range)
        repo = RuntimeMetricRepository(db)
        records = repo.recent_activity(limit=limit, since=since)
        if decision:
            records = [r for r in records if r.decision == decision]
        items = []
        for m in records:
            ts = m.timestamp
            if hasattr(ts, "isoformat"):
                ts_str = ts.isoformat()
            else:
                ts_str = str(ts)
            items.append(
                RuntimeMetricResponse(
                    id=m.id,
                    timestamp=ts_str,
                    tool=m.tool,
                    action=m.action,
                    decision=m.decision,
                    matched_rule=m.matched_rule,
                    reason=m.reason,
                    execution_time_ms=m.execution_time_ms,
                    tool_latency_ms=m.tool_latency_ms,
                    execution_status=m.execution_status,
                    risk_level=m.risk_level or _risk_level(m.decision, m.execution_status),
                    request_data=m.request_data,
                    tool_output=m.tool_output,
                )
            )
        return items
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
