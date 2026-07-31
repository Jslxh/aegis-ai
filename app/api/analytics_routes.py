from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database.session import get_db
from app.database.repositories.analytics_repository import AnalyticsRepository
from app.services.analytics_service import AnalyticsService
from app.auth.dependencies import require_role
from app.models.analytics import (
    PolicyEffectivenessResult,
    MostTriggeredRulesResult,
    MostDangerousToolsResult,
    BlockedRequestsResult,
    HITLStatisticsResult,
    ResponseTimeStats,
    RiskDistributionResult,
    AnalyticsReportResponse,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/policy-effectiveness", response_model=PolicyEffectivenessResult)
def get_policy_effectiveness(
    time_range: str = Query("30d", description="Time range: 1h, 24h, 7d, 30d, all"),
    _: dict = Depends(require_role("auditor")),
    db: Session = Depends(get_db),
):
    try:
        service = AnalyticsService(db)
        return PolicyEffectivenessResult(**service.policy_effectiveness(time_range))
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/most-triggered-rules", response_model=MostTriggeredRulesResult)
def get_most_triggered_rules(
    time_range: str = Query("30d", description="Time range: 1h, 24h, 7d, 30d, all"),
    _: dict = Depends(require_role("auditor")),
    db: Session = Depends(get_db),
):
    try:
        service = AnalyticsService(db)
        return MostTriggeredRulesResult(**service.most_triggered_rules(time_range))
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/most-dangerous-tools", response_model=MostDangerousToolsResult)
def get_most_dangerous_tools(
    time_range: str = Query("30d", description="Time range: 1h, 24h, 7d, 30d, all"),
    _: dict = Depends(require_role("auditor")),
    db: Session = Depends(get_db),
):
    try:
        service = AnalyticsService(db)
        return MostDangerousToolsResult(**service.most_dangerous_tools(time_range))
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/blocked-requests", response_model=BlockedRequestsResult)
def get_blocked_requests(
    time_range: str = Query("30d", description="Time range: 1h, 24h, 7d, 30d, all"),
    _: dict = Depends(require_role("auditor")),
    db: Session = Depends(get_db),
):
    try:
        service = AnalyticsService(db)
        return BlockedRequestsResult(**service.blocked_requests(time_range))
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/hitl-statistics", response_model=HITLStatisticsResult)
def get_hitl_statistics(
    time_range: str = Query("30d", description="Time range: 1h, 24h, 7d, 30d, all"),
    _: dict = Depends(require_role("auditor")),
    db: Session = Depends(get_db),
):
    try:
        service = AnalyticsService(db)
        return HITLStatisticsResult(**service.hitl_statistics(time_range))
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/avg-response-time", response_model=ResponseTimeStats)
def get_avg_response_time(
    time_range: str = Query("30d", description="Time range: 1h, 24h, 7d, 30d, all"),
    _: dict = Depends(require_role("auditor")),
    db: Session = Depends(get_db),
):
    try:
        service = AnalyticsService(db)
        return ResponseTimeStats(**service.avg_response_time(time_range))
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/risk-distribution", response_model=RiskDistributionResult)
def get_risk_distribution(
    time_range: str = Query("30d", description="Time range: 1h, 24h, 7d, 30d, all"),
    _: dict = Depends(require_role("auditor")),
    db: Session = Depends(get_db),
):
    try:
        service = AnalyticsService(db)
        return RiskDistributionResult(**service.risk_distribution(time_range))
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


@router.post("/reports/daily", response_model=AnalyticsReportResponse)
def generate_daily_report(
    date: str = Query(..., description="Date to generate report for (YYYY-MM-DD)"),
    _: dict = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    try:
        service = AnalyticsService(db)
        result = service.generate_daily_report(date)
        return AnalyticsReportResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.post("/reports/monthly", response_model=AnalyticsReportResponse)
def generate_monthly_report(
    month: str = Query(..., description="Month to generate report for (YYYY-MM)"),
    _: dict = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    try:
        service = AnalyticsService(db)
        result = service.generate_monthly_report(month)
        return AnalyticsReportResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/reports", response_model=List[AnalyticsReportResponse])
def list_reports(
    report_type: Optional[str] = Query(None, description="Filter by report type: daily, monthly"),
    limit: int = Query(50, ge=1, le=500),
    _: dict = Depends(require_role("auditor")),
    db: Session = Depends(get_db),
):
    try:
        service = AnalyticsService(db)
        reports = service.list_reports(report_type=report_type, limit=limit)
        return [AnalyticsReportResponse(**r) for r in reports]
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/reports/{report_type}/{period}", response_model=AnalyticsReportResponse)
def get_report(
    report_type: str,
    period: str,
    _: dict = Depends(require_role("auditor")),
    db: Session = Depends(get_db),
):
    try:
        service = AnalyticsService(db)
        report = service.get_report(report_type, period)
        if not report:
            raise HTTPException(status_code=404, detail=f"Report {report_type} for {period} not found")
        return AnalyticsReportResponse(**report)
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
