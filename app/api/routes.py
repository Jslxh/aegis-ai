import time as time_module
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from opentelemetry.trace import SpanKind, StatusCode
from app.core.policy_engine import PolicyEngine
from app.core.guardrail import Guardrail
from app.core.executor import ToolExecutor
from app.audit.logger import AuditLogger
from app.simulator.simulation import Simulation
from app.hitl.approval import BaseApprovalQueue, MockApprovalQueue
from app.database.config import HITLConfig
from app.models.request import ActionRequest
from app.models.response import EvaluationResult, ExecutionResult, SimulationResult, DryRunResult
from app.models.policy import (
    PolicyCreate,
    PolicyUpdate,
    PolicyResponse,
    PolicyConflict,
    PolicyValidationResult,
    RulePreviewRequest,
    RulePreviewResult,
    PolicyExportResult,
)
from app.database.session import get_db_optional
from app.database.repositories.audit_log_repository import AuditLogRepository
from app.database.repositories.execution_history_repository import ExecutionHistoryRepository
from app.database.repositories.policy_repository import PolicyRepository
from app.database.repositories.runtime_metric_repository import RuntimeMetricRepository
from app.auth.dependencies import require_role, optional_require_role
from app.services.audit_service import AuditService
from app.services.policy_service import (
    model_to_response,
    validate_policy,
    detect_conflicts,
    preview_rule,
    export_policies,
    import_policies,
)
from app.observability import (
    active_executions,
    emit_security_event,
    get_logger,
    get_tracer,
    record_db_operation,
    record_execution,
    record_failure,
    set_context,
)
from app.observability.security import (
    POLICY_BLOCKED,
    POLICY_CREATED,
    POLICY_UPDATED,
    POLICY_DELETED,
)

router = APIRouter()

policy_engine = PolicyEngine()
guardrail = Guardrail()
executor = ToolExecutor()
audit = AuditLogger()
simulation = Simulation()
approval_queue: BaseApprovalQueue = MockApprovalQueue()

logger = get_logger("guardrail.api")


def _try_persist(
    db: Optional[Session],
    action: callable,
    operation: str = "db_write",
) -> None:
    """Attempt a DB operation and silently skip if DB is unavailable or tables don't exist."""
    if not db:
        return
    try:
        action()
        db.commit()
        record_db_operation(operation, "success")
    except SQLAlchemyError as e:
        db.rollback()
        record_failure("persistence", "db_error")
        record_db_operation(operation, "error")
        logger.warning(
            "persistence failure",
            extra={
                "event": "persistence.failure",
                "operation": operation,
                "error": str(e)[:200],
            },
        )


def _risk_level(decision: str) -> str:
    if decision == "block":
        return "critical"
    if decision == "require_hitl":
        return "high"
    if decision == "log_and_allow":
        return "medium"
    return "low"


def _record_metric(
    db: Optional[Session],
    req_dict: Dict[str, Any],
    result: Dict[str, Any],
    execution_status: str,
    total_time_ms: float,
    tool_latency_ms: float,
    tool_output: Dict[str, Any],
    correlation_id: Optional[str] = None,
    request_id: Optional[str] = None,
    execution_id: Optional[str] = None,
) -> None:
    _try_persist(
        db,
        lambda: RuntimeMetricRepository(db).create_metric(
            tool=req_dict.get("tool", ""),
            action=req_dict.get("action", ""),
            decision=result.get("decision", ""),
            matched_rule=result.get("matched_rule"),
            reason=result.get("reason"),
            execution_time_ms=round(total_time_ms, 2),
            tool_latency_ms=round(tool_latency_ms, 2) if tool_latency_ms > 0 else None,
            execution_status=execution_status,
            risk_level=_risk_level(result.get("decision", "")),
            request_data=req_dict,
            tool_output=tool_output,
            correlation_id=correlation_id,
            request_id=request_id,
            execution_id=execution_id,
        ),
    )


@router.get("/")
def root():
    return {
        "message": "Welcome to Guardrail AI"
    }


@router.get("/about")
def about():
    return {
        "project": "Guardrail AI",
        "version": "1.0.0",
        "description": "Runtime Action Guardrail Platform",
        "features": [
            "Policy Engine",
            "Action Guardrail",
            "Audit Logging",
            "Simulation Harness",
            "Dry Run Mode"
        ]
    }


@router.get("/health")
def health():
    return {
        "status": "healthy"
    }


@router.post("/evaluate", response_model=EvaluationResult)
def evaluate(
    request: ActionRequest,
    _: None = Depends(optional_require_role("operator")),
):
    req_dict = request.model_dump()
    result = guardrail.evaluate(req_dict)
    return EvaluationResult(**result)


@router.post("/execute")
def execute(
    request: ActionRequest,
    dry_run: bool = Query(False),
    _: None = Depends(optional_require_role("operator")),
    db: Session = Depends(get_db_optional),
):
    start_time = time_module.monotonic()
    req_dict = request.model_dump()

    correlation_id = AuditService.generate_correlation_id()
    request_id = AuditService.generate_request_id()
    execution_id = AuditService.generate_execution_id()
    trace_context = {
        "correlation_id": correlation_id,
        "request_id": request_id,
        "execution_id": execution_id,
        "risk_level": _risk_level(""),
    }

    set_context(
        correlation_id=correlation_id,
        request_id=request_id,
        execution_id=execution_id,
        tool=req_dict.get("tool"),
        action=req_dict.get("action"),
    )

    result = guardrail.evaluate(req_dict)
    trace_context["risk_level"] = _risk_level(result["decision"])

    is_dry_run = dry_run or request.dry_run

    if is_dry_run:
        return _handle_dry_run(req_dict, result)

    decision = result["decision"]
    tool_name = req_dict.get("tool", "")
    action_name = req_dict.get("action", "")

    active_executions.inc()
    span = get_tracer().start_span(
        "guardrail.execute",
        kind=SpanKind.INTERNAL,
        attributes={
            "tool": tool_name,
            "action": action_name,
            "decision": decision,
            "matched_rule": result.get("matched_rule") or "",
            "execution_id": execution_id,
            "correlation_id": correlation_id,
            "request_id": request_id,
        },
    )

    try:
        audit.log(req_dict, result, **trace_context)

        tool_start = time_module.monotonic()
        if decision == "block":
            execution_status = "blocked"
            output = {"status": "Blocked by Guardrail"}
            tool_latency = 0.0
            emit_security_event(
                POLICY_BLOCKED,
                severity="high",
                outcome="blocked",
                tool=tool_name,
                action=action_name,
                matched_rule=result.get("matched_rule"),
                reason=result.get("reason"),
                correlation_id=correlation_id,
                execution_id=execution_id,
            )

        elif decision == "require_hitl":
            execution_status = "waiting_for_human"
            output = {"status": "Pending Human Approval"}
            tool_latency = 0.0
            _request_hitl_approval(
                execution_id,
                req_dict,
                result,
                correlation_id=correlation_id,
                request_id=request_id,
            )

        else:
            output = executor.execute(req_dict, dry_run=request.dry_run)
            tool_latency = (time_module.monotonic() - tool_start) * 1000

            if output.get("status") == "error":
                execution_status = "failed"
                record_failure("tool_execution", "tool_error")
            else:
                execution_status = "executed_with_logging" if decision == "log_and_allow" else "executed"

        total_time = (time_module.monotonic() - start_time) * 1000

        _try_persist(
            db,
            lambda: ExecutionHistoryRepository(db).create_record(
                req_dict, result, execution_status, output,
                correlation_id=correlation_id,
                request_id=request_id,
                execution_id=execution_id,
            ),
            operation="execution_history",
        )
        _record_metric(db, req_dict, result, execution_status, total_time, tool_latency, output,
                       correlation_id=correlation_id, request_id=request_id, execution_id=execution_id)

        record_execution(
            tool_name, action_name, decision, execution_status,
            total_ms=total_time, tool_latency_ms=tool_latency,
        )

        span.set_attribute("execution.status", execution_status)
        span.set_attribute("execution.duration_ms", round(total_time, 2))
        if execution_status == "failed":
            span.set_status(StatusCode.ERROR, "tool execution failed")
        else:
            span.set_status(StatusCode.OK)

        return ExecutionResult(
            status=execution_status,
            decision=decision,
            matched_rule=result.get("matched_rule"),
            reason=result.get("reason"),
            tool_output=output,
            correlation_id=correlation_id,
            request_id=request_id,
            execution_id=execution_id,
        )
    except Exception as exc:  # noqa: BLE001
        span.record_exception(exc)
        span.set_status(StatusCode.ERROR, str(exc))
        record_failure("execution", "unexpected_exception")
        logger.error(
            "execution failed",
            extra={
                "event": "execution.failed",
                "tool": tool_name,
                "action": action_name,
                "correlation_id": correlation_id,
                "execution_id": execution_id,
            },
        )
        raise
    finally:
        active_executions.dec()
        span.end()


def _request_hitl_approval(
    execution_id: str,
    req_dict: Dict[str, Any],
    result: Dict[str, Any],
    correlation_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> None:
    """Submit a require_hitl action to the approval queue without failing the request."""
    expires_at = datetime.now().timestamp() + HITLConfig.EXPIRY_HOURS * 3600
    expires_dt = datetime.fromtimestamp(expires_at)
    try:
        approval_queue.request_approval(
            execution_id,
            req_dict,
            decision=result.get("decision", "require_hitl"),
            reason=result.get("reason", ""),
            expires_at=expires_dt,
        )
    except Exception:  # noqa: BLE001
        record_failure("hitl", "approval_queue_error")
        logger.warning(
            "approval queue submission failed",
            extra={
                "event": "hitl.submit_failed",
                "execution_id": execution_id,
                "correlation_id": correlation_id,
                "request_id": request_id,
            },
        )


def _handle_dry_run(req_dict: Dict[str, Any], result: Dict[str, Any]) -> DryRunResult:
    decision = result["decision"]
    matched_rule = result.get("matched_rule")
    reason = result.get("reason") or ""

    would_execute = decision in ("allow", "log_and_allow")
    would_block = decision == "block"
    would_require_hitl = decision == "require_hitl"

    risk_map = {
        "block": "critical",
        "require_hitl": "high",
        "log_and_allow": "medium",
        "allow": "low",
    }
    risk_level = risk_map.get(decision, "unknown")

    simulated = executor.simulate(req_dict)

    audit_preview = {
        "tool": req_dict.get("tool"),
        "action": req_dict.get("action"),
        "decision": decision,
        "matched_rule": matched_rule,
        "reason": reason,
        "request": req_dict,
        "timestamp": datetime.utcnow().isoformat(),
        "logged": False,
        "message": "Audit entry would be created on actual execution",
    }

    return DryRunResult(
        decision=decision,
        matched_rule=matched_rule,
        reason=reason,
        would_execute=would_execute,
        would_block=would_block,
        would_require_hitl=would_require_hitl,
        risk_level=risk_level,
        audit_preview=audit_preview,
        simulated_output=simulated.get("simulated_output"),
    )


@router.get("/simulate", response_model=SimulationResult)
def simulate(
    _: None = Depends(optional_require_role("operator")),
):
    res = simulation.run()
    return SimulationResult(**res)


@router.get("/audit")
def get_logs(
    _: dict = Depends(require_role("auditor")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        return {"detail": "Database not available", "logs": []}
    try:
        records = AuditLogRepository(db).list_recent(limit=100)
        return [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "tool": r.tool,
                "action": r.action,
                "request_data": r.request_data,
                "decision": r.decision,
                "matched_rule": r.matched_rule,
                "reason": r.reason,
            }
            for r in records
        ]
    except SQLAlchemyError:
        return {"detail": "Tables not initialized. Run migrations.", "logs": []}


@router.get("/history")
def get_history(
    _: dict = Depends(require_role("auditor")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        return {"detail": "Database not available", "history": []}
    try:
        records = ExecutionHistoryRepository(db).list_recent(limit=100)
        return [
            {
                "id": r.id,
                "tool": r.tool,
                "action": r.action,
                "request_data": r.request_data,
                "decision": r.decision,
                "matched_rule": r.matched_rule,
                "execution_status": r.execution_status,
                "tool_output": r.tool_output,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]
    except SQLAlchemyError:
        return {"detail": "Tables not initialized. Run migrations.", "history": []}


# ---------------------------------------------------------------------------
# Policy Management CRUD
# ---------------------------------------------------------------------------


@router.get("/policies", response_model=Dict[str, Any])
def list_policies(
    enabled_only: bool = Query(False, description="Filter to only enabled policies"),
    tool: Optional[str] = Query(None, description="Filter by tool"),
    action: Optional[str] = Query(None, description="Filter by action"),
    _: dict = Depends(require_role("viewer")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        return {"detail": "Database not available", "rules": [], "total": 0}

    try:
        repo = PolicyRepository(db)
        models = repo.list_all(enabled_only=enabled_only, tool=tool, action=action)
        rules = [model_to_response(m).model_dump() for m in models]
        total = len(rules)
        enabled_count = sum(1 for r in rules if r.get("enabled", True))
        return {
            "rules": rules,
            "total": total,
            "enabled_count": enabled_count,
            "disabled_count": total - enabled_count,
        }
    except SQLAlchemyError:
        return {"detail": "Tables not initialized. Run migrations.", "rules": [], "total": 0}


@router.get("/policies/export", response_model=PolicyExportResult)
def export_policies_endpoint(
    _: dict = Depends(require_role("auditor")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        repo = PolicyRepository(db)
        yaml_content = export_policies(repo)
        import yaml as yaml_lib
        parsed = yaml_lib.safe_load(yaml_content)
        rules = parsed.get("rules", []) if parsed else []
        return PolicyExportResult(policies=rules, format="yaml")
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


@router.get("/policies/export/yaml")
def export_policies_yaml(
    _: dict = Depends(require_role("auditor")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        repo = PolicyRepository(db)
        yaml_str = export_policies(repo)
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            content=yaml_str,
            media_type="text/yaml",
            headers={"Content-Disposition": "attachment; filename=policies.yaml"},
        )
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


@router.post("/policies/validate", response_model=PolicyValidationResult)
def validate_policy_endpoint(
    policy: PolicyCreate,
    _: dict = Depends(require_role("operator")),
):
    result = validate_policy(policy.model_dump())
    return result


@router.post("/policies/check-conflicts", response_model=List[PolicyConflict])
def check_conflicts(
    policy: PolicyCreate,
    _: dict = Depends(require_role("operator")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        return []

    try:
        repo = PolicyRepository(db)
        return detect_conflicts(
            repo,
            tool=policy.tool,
            action=policy.action,
            decision=policy.decision,
        )
    except SQLAlchemyError:
        return []


@router.post("/policies/preview", response_model=RulePreviewResult)
def preview_policy(
    payload: RulePreviewRequest,
    _: dict = Depends(require_role("operator")),
):
    result = preview_rule(payload.policy.model_dump(), payload.request)
    return result


@router.post("/policies/import")
def import_policies_endpoint(
    yaml_body: str = Body(..., media_type="text/plain", description="YAML content with rules"),
    _: dict = Depends(require_role("admin")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        repo = PolicyRepository(db)
        created, updated, errors = import_policies(repo, yaml_body)
        return {
            "imported": True,
            "created": created,
            "updated": updated,
            "errors": errors,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Import failed: {e}")


@router.get("/policies/{rule_id}", response_model=PolicyResponse)
def get_policy(
    rule_id: str,
    _: dict = Depends(require_role("viewer")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        repo = PolicyRepository(db)
        model = repo.find_by_rule_id(rule_id)
        if not model:
            raise HTTPException(status_code=404, detail=f"Policy '{rule_id}' not found")
        return model_to_response(model)
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.post("/policies", response_model=PolicyResponse, status_code=201)
def create_policy(
    policy: PolicyCreate,
    current_user: dict = Depends(require_role("security_analyst")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    validation = validate_policy(policy.model_dump())
    if not validation.valid:
        raise HTTPException(status_code=422, detail={"errors": validation.errors, "warnings": validation.warnings})

    try:
        repo = PolicyRepository(db)
        existing = repo.find_by_rule_id(policy.rule_id)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Policy with rule_id '{policy.rule_id}' already exists",
            )

        conflicts = detect_conflicts(
            repo,
            tool=policy.tool,
            action=policy.action,
            decision=policy.decision,
        )

        model = repo.create_policy(policy.model_dump())
        db.commit()

        emit_security_event(
            POLICY_CREATED,
            severity="info",
            outcome="success",
            rule_id=model.rule_id,
            tool=model.tool,
            action=model.action,
            decision=model.decision,
            actor=current_user.get("username"),
        )

        response = model_to_response(model)
        if conflicts:
            response_dict = response.model_dump()
            response_dict["warnings"] = [c.description for c in conflicts]
            return response_dict

        return response
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.put("/policies/{rule_id}", response_model=PolicyResponse)
def update_policy(
    rule_id: str,
    policy: PolicyUpdate,
    current_user: dict = Depends(require_role("security_analyst")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    update_data = {k: v for k, v in policy.model_dump().items() if v is not None}

    try:
        repo = PolicyRepository(db)
        existing = repo.find_by_rule_id(rule_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Policy '{rule_id}' not found")

        conflicts: List[PolicyConflict] = []
        if "tool" in update_data or "action" in update_data or "decision" in update_data:
            tool = update_data.get("tool", existing.tool)
            action = update_data.get("action", existing.action)
            decision = update_data.get("decision", existing.decision)
            conflicts = detect_conflicts(
                repo,
                tool=tool,
                action=action,
                decision=decision,
                exclude_rule_id=rule_id,
            )

        model = repo.update_policy(rule_id, update_data)
        db.commit()

        emit_security_event(
            POLICY_UPDATED,
            severity="info",
            outcome="success",
            rule_id=rule_id,
            actor=current_user.get("username"),
            changes=list(update_data.keys()),
        )

        response = model_to_response(model)
        response_dict = response.model_dump()

        if conflicts:
            response_dict["warnings"] = [c.description for c in conflicts]

        return response_dict
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.delete("/policies/{rule_id}")
def delete_policy(
    rule_id: str,
    current_user: dict = Depends(require_role("admin")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        repo = PolicyRepository(db)
        deleted = repo.delete_by_rule_id(rule_id)
        db.commit()
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Policy '{rule_id}' not found")
        emit_security_event(
            POLICY_DELETED,
            severity="warning",
            outcome="success",
            rule_id=rule_id,
            actor=current_user.get("username"),
        )
        return {"deleted": True, "rule_id": rule_id}
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.post("/policies/{rule_id}/toggle", response_model=PolicyResponse)
def toggle_policy(
    rule_id: str,
    enabled: bool = Body(..., embed=True),
    _: dict = Depends(require_role("security_analyst")),
    db: Optional[Session] = Depends(get_db_optional),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        repo = PolicyRepository(db)
        model = repo.find_by_rule_id(rule_id)
        if not model:
            raise HTTPException(status_code=404, detail=f"Policy '{rule_id}' not found")
        repo.update_policy(rule_id, {"enabled": enabled})
        db.commit()
        model = repo.find_by_rule_id(rule_id)
        return model_to_response(model)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
