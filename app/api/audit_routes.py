from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database.session import get_db_optional
from app.auth.dependencies import require_role
from app.models.audit import (
    AuditRecord,
    AuditSearchResult,
    AuditTimelineResult,
    AuditTimelinePoint,
    IntegrityResult,
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


def _get_service(db: Session) -> AuditService:
    return AuditService(db)


@router.get("/logs", response_model=AuditSearchResult)
def search_audit_logs(
    tool: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    decision: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    correlation_id: Optional[str] = Query(None),
    request_id: Optional[str] = Query(None),
    execution_id: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Free-text search over rule/reason/IDs"),
    start_date: Optional[str] = Query(None, description="ISO timestamp (inclusive)"),
    end_date: Optional[str] = Query(None, description="ISO timestamp (inclusive)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    _: dict = Depends(require_role("auditor")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        service = _get_service(db)
        return service.search(
            page=page,
            page_size=page_size,
            tool=tool,
            action=action,
            decision=decision,
            status=status,
            event_type=event_type,
            risk_level=risk_level,
            correlation_id=correlation_id,
            request_id=request_id,
            execution_id=execution_id,
            source=source,
            actor=actor,
            search=search,
            start_date=start_date,
            end_date=end_date,
        )
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/timeline", response_model=AuditTimelineResult)
def get_audit_timeline(
    granularity: str = Query("hour", description="Granularity: hour, day"),
    limit: int = Query(168, ge=1, le=1000),
    _: dict = Depends(require_role("auditor")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        service = _get_service(db)
        result = service.timeline(granularity=granularity, limit=limit)
        return AuditTimelineResult(
            granularity=result["granularity"],
            points=[AuditTimelinePoint(**p) for p in result["points"]],
        )
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/correlation/{correlation_id}", response_model=list[AuditRecord])
def get_correlation_chain(
    correlation_id: str,
    _: dict = Depends(require_role("auditor")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        service = _get_service(db)
        return service.by_correlation(correlation_id)
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/verify", response_model=IntegrityResult)
def verify_audit_integrity(
    limit: Optional[int] = Query(None, ge=1, le=1_000_000),
    _: dict = Depends(require_role("auditor")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        service = _get_service(db)
        return service.verify_integrity(limit=limit)
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/export/csv")
def export_audit_csv(
    tool: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    decision: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    correlation_id: Optional[str] = Query(None),
    request_id: Optional[str] = Query(None),
    execution_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(5000, ge=1, le=50_000),
    _: dict = Depends(require_role("auditor")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        service = _get_service(db)
        filters = service._build_filters(
            tool=tool,
            action=action,
            decision=decision,
            status=status,
            risk_level=risk_level,
            correlation_id=correlation_id,
            request_id=request_id,
            execution_id=execution_id,
            search=search,
            start_date=start_date,
            end_date=end_date,
        )
        content = service.export_csv(filters, limit=limit)
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
        )
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/export/json")
def export_audit_json(
    tool: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    decision: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    correlation_id: Optional[str] = Query(None),
    request_id: Optional[str] = Query(None),
    execution_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(5000, ge=1, le=50_000),
    _: dict = Depends(require_role("auditor")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        service = _get_service(db)
        filters = service._build_filters(
            tool=tool,
            action=action,
            decision=decision,
            status=status,
            risk_level=risk_level,
            correlation_id=correlation_id,
            request_id=request_id,
            execution_id=execution_id,
            search=search,
            start_date=start_date,
            end_date=end_date,
        )
        items = service.export_json(filters, limit=limit)
        return Response(
            content=__import__("json").dumps(items, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=audit_logs.json"},
        )
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
