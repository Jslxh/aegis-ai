"""Human-in-the-loop approval workflow REST API.

Endpoints:
    GET    /approvals              List approval requests (filter + pagination)
    GET    /approvals/stats        HITL workflow statistics
    GET    /approvals/{id}         Fetch a single approval request
    POST   /approvals/{id}/approve Approve a pending request
    POST   /approvals/{id}/reject  Reject a pending request
    POST   /approvals/{id}/expire  Expire a pending request (operator tool)
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.auth.dependencies import require_role
from app.database.session import get_db_optional
from app.database.repositories.hitl_request_repository import HITLRequestRepository
from app.models.hitl import (
    ApprovalDecision,
    ApprovalListResult,
    ApprovalRequestResponse,
    ApprovalStats,
)
from app.observability import emit_security_event
from app.observability.security import HITL_APPROVED, HITL_DENIED

router = APIRouter(prefix="/approvals", tags=["approvals"])

HITL_STAT_ALIASES = {
    "pending": "pending",
    "approved": "approved",
    "rejected": "rejected",
    "expired": "expired",
    "all": None,
}


def _not_found(request_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Approval request '{request_id}' not found")


def _unresolvable(model) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail=f"Approval request is already {model.status}",
    )


def _to_response(model) -> ApprovalRequestResponse:
    return ApprovalRequestResponse(**model.to_dict())


@router.get("", response_model=ApprovalListResult)
def list_approvals(
    status: Optional[str] = Query(None, description="pending, approved, rejected, expired, all"),
    tool: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    _: dict = Depends(require_role("auditor")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        repo = HITLRequestRepository(db)
        if status and status not in HITL_STAT_ALIASES:
            raise HTTPException(status_code=422, detail="Invalid status filter")
        effective_status = HITL_STAT_ALIASES.get(status or "pending")
        total = repo.count_requests(status=effective_status, tool=tool)
        models = repo.list_requests(
            status=effective_status,
            tool=tool,
            skip=(page - 1) * page_size,
            limit=page_size,
        )
        pages = max(1, -(-total // page_size)) if total else 1
        return ApprovalListResult(
            items=[_to_response(m) for m in models],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/stats", response_model=ApprovalStats)
def approval_stats(
    _: dict = Depends(require_role("auditor")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        repo = HITLRequestRepository(db)
        return ApprovalStats(**repo.stats())
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/{request_id}", response_model=ApprovalRequestResponse)
def get_approval(
    request_id: str,
    _: dict = Depends(require_role("auditor")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        repo = HITLRequestRepository(db)
        model = repo.find_by_request_id(request_id)
        if not model:
            raise _not_found(request_id)
        return _to_response(model)
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.post("/{request_id}/approve", response_model=ApprovalRequestResponse)
def approve_request(
    request_id: str,
    payload: ApprovalDecision,
    current_user: dict = Depends(require_role("security_analyst")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        repo = HITLRequestRepository(db)
        model = repo.find_by_request_id(request_id)
        if not model:
            raise _not_found(request_id)
        if model.status != "pending":
            raise _unresolvable(model)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if model.expires_at and model.expires_at < now:
            repo.expire(request_id)
            db.commit()
            raise HTTPException(
                status_code=410,
                detail=f"Approval request expired at {model.expires_at.isoformat()}",
            )
        model = repo.approve(
            request_id,
            reason=payload.reason,
            reviewer=current_user["username"],
            comments=payload.comments,
        )
        
        # Execute the actual tool action upon approval
        from app.core.executor import ToolExecutor
        from app.database.models.execution_history import ExecutionHistoryModel
        
        executor = ToolExecutor()
        exec_output = executor.execute(model.request_data)
        
        # If there is a corresponding execution history record, update its status and output
        exec_id = request_id[5:] if request_id.startswith("exec_") else request_id
        exec_record = (
            db.query(ExecutionHistoryModel)
            .filter(
                (ExecutionHistoryModel.execution_id == request_id) |
                (ExecutionHistoryModel.execution_id == exec_id)
            )
            .first()
        )
        if exec_record:
            if exec_output.get("status") == "error":
                exec_record.execution_status = "failed"
            else:
                exec_record.execution_status = "executed"
            exec_record.tool_output = exec_output

        db.commit()
        emit_security_event(
            HITL_APPROVED,
            severity="info",
            outcome="approved",
            request_id=request_id,
            reviewer=current_user["username"],
            tool=model.tool,
            action=model.action,
            reason=payload.reason,
        )
        return _to_response(model)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.post("/{request_id}/reject", response_model=ApprovalRequestResponse)
def reject_request(
    request_id: str,
    payload: ApprovalDecision,
    current_user: dict = Depends(require_role("security_analyst")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        repo = HITLRequestRepository(db)
        model = repo.find_by_request_id(request_id)
        if not model:
            raise _not_found(request_id)
        if model.status != "pending":
            raise _unresolvable(model)
        model = repo.reject(
            request_id,
            reason=payload.reason,
            reviewer=current_user["username"],
            comments=payload.comments,
        )
        db.commit()
        emit_security_event(
            HITL_DENIED,
            severity="warning",
            outcome="rejected",
            request_id=request_id,
            reviewer=current_user["username"],
            tool=model.tool,
            action=model.action,
            reason=payload.reason,
        )
        return _to_response(model)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.post("/{request_id}/expire", response_model=ApprovalRequestResponse)
def expire_request(
    request_id: str,
    _: dict = Depends(require_role("security_analyst")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        repo = HITLRequestRepository(db)
        model = repo.find_by_request_id(request_id)
        if not model:
            raise _not_found(request_id)
        if model.status != "pending":
            raise _unresolvable(model)
        model = repo.expire(request_id)
        db.commit()
        return _to_response(model)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
