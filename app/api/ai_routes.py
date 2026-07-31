import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.services.groq_service import GroqService
from app.models.request import (
    ExplainRequest,
    RiskAnalysisRequest,
    HITLSummaryRequest,
    AuditSummaryRequest,
    SimulationSummaryRequest,
)
from app.models.ai import AIGeneratedContentResponse
from app.database.session import get_db
from app.database.repositories.ai_content_repository import AIGeneratedContentRepository
from app.database.repositories.execution_history_repository import ExecutionHistoryRepository
from app.database.repositories.audit_log_repository import AuditLogRepository
from app.database.repositories.simulation_run_repository import SimulationRunRepository
from app.auth.dependencies import require_role, optional_require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])

groq: GroqService | None = None


def get_groq() -> GroqService:
    if groq is None:
        raise HTTPException(status_code=503, detail="Groq service not initialized")
    return groq


def _persist(
    db: Session,
    content_type: str,
    source_type: str,
    source_id: int,
    result: dict,
    tool: Optional[str] = None,
    action: Optional[str] = None,
    decision: Optional[str] = None,
    matched_rule: Optional[str] = None,
) -> None:
    repo = AIGeneratedContentRepository(db)
    repo.create_content(
        content_type=content_type,
        source_type=source_type,
        source_id=source_id,
        tool=tool,
        action=action,
        decision=decision,
        matched_rule=matched_rule,
        explanation=result.get("explanation"),
        risk_analysis=result.get("risk_analysis"),
        risk_level=result.get("risk_level"),
        recommendations=result.get("recommendations"),
        confidence=result.get("confidence"),
        summary=result.get("summary"),
        model=result.get("model"),
        latency_ms=result.get("latency"),
    )
    db.commit()


def _find_stored(db: Session, source_type: str, source_id: int, content_type: str):
    repo = AIGeneratedContentRepository(db)
    return repo.find_by_source(source_type, source_id, content_type=content_type)


def _to_response(model) -> AIGeneratedContentResponse:
    return AIGeneratedContentResponse(
        id=model.id,
        content_type=model.content_type,
        source_type=model.source_type,
        source_id=model.source_id,
        tool=model.tool,
        action=model.action,
        decision=model.decision,
        matched_rule=model.matched_rule,
        explanation=model.explanation,
        risk_analysis=model.risk_analysis,
        risk_level=model.risk_level,
        recommendations=model.recommendations,
        confidence=model.confidence,
        summary=model.summary,
        model=model.model,
        latency_ms=model.latency_ms,
        created_at=model.created_at.isoformat() if model.created_at else None,
    )


@router.post("/explain")
def explain_decision(
    payload: ExplainRequest,
    _: None = Depends(optional_require_role("operator")),
    db: Session = Depends(get_db),
):
    svc = get_groq()
    result = svc.explain_decision(
        matched_rule=payload.matched_rule,
        decision=payload.decision,
        reason=payload.reason,
        request=payload.request,
    )
    if not result["success"]:
        raise HTTPException(status_code=502, detail=result.get("error", "Groq API call failed"))

    if payload.execution_id:
        _persist(
            db,
            content_type="explanation",
            source_type="execution",
            source_id=payload.execution_id,
            result=result,
            tool=payload.request.get("tool"),
            action=payload.request.get("action"),
            decision=payload.decision,
            matched_rule=payload.matched_rule,
        )
    return result


@router.post("/risk-analysis")
def risk_analysis(
    payload: RiskAnalysisRequest,
    _: None = Depends(optional_require_role("operator")),
    db: Session = Depends(get_db),
):
    svc = get_groq()
    result = svc.analyze_risk(
        tool=payload.tool,
        action=payload.action,
        parameters=payload.parameters,
        decision=payload.decision,
    )
    if not result["success"]:
        raise HTTPException(status_code=502, detail=result.get("error", "Groq API call failed"))

    if payload.execution_id:
        _persist(
            db,
            content_type="risk_analysis",
            source_type="execution",
            source_id=payload.execution_id,
            result=result,
            tool=payload.tool,
            action=payload.action,
            decision=payload.decision,
        )
    return result


@router.post("/hitl-summary")
def hitl_summary(
    payload: HITLSummaryRequest,
    _: None = Depends(optional_require_role("auditor")),
    db: Session = Depends(get_db),
):
    svc = get_groq()
    result = svc.hitl_summary(
        request=payload.request,
        decision=payload.decision,
        reason=payload.reason,
    )
    if not result["success"]:
        raise HTTPException(status_code=502, detail=result.get("error", "Groq API call failed"))

    _persist(
        db,
        content_type="hitl_summary",
        source_type="hitl",
        source_id=0,
        result=result,
        tool=payload.request.get("tool"),
        action=payload.request.get("action"),
        decision=payload.decision,
    )
    return result


@router.post("/audit-summary")
def audit_summary(
    payload: AuditSummaryRequest,
    _: None = Depends(optional_require_role("auditor")),
    db: Session = Depends(get_db),
):
    svc = get_groq()
    result = svc.audit_summary(record=payload.record)
    if not result["success"]:
        raise HTTPException(status_code=502, detail=result.get("error", "Groq API call failed"))

    if payload.audit_id:
        _persist(
            db,
            content_type="audit_summary",
            source_type="audit",
            source_id=payload.audit_id,
            result=result,
            tool=payload.record.get("tool"),
            action=payload.record.get("action"),
            decision=payload.record.get("decision"),
            matched_rule=payload.record.get("matched_rule"),
        )
    return result


@router.post("/simulation-summary")
def simulation_summary(
    payload: SimulationSummaryRequest,
    _: None = Depends(optional_require_role("auditor")),
    db: Session = Depends(get_db),
):
    svc = get_groq()
    result = svc.simulation_analysis(
        summary=payload.summary,
        results=payload.results,
    )
    if not result["success"]:
        raise HTTPException(status_code=502, detail=result.get("error", "Groq API call failed"))

    if payload.simulation_id:
        _persist(
            db,
            content_type="simulation_analysis",
            source_type="simulation",
            source_id=payload.simulation_id,
            result=result,
            decision=payload.summary.get("decision"),
        )
    return result


# ---------------------------------------------------------------------------
# Retrieval endpoints (stored AI content, generated on demand if absent)
# ---------------------------------------------------------------------------


@router.get("/executions/{execution_id}/explanation", response_model=AIGeneratedContentResponse)
def get_execution_explanation(
    execution_id: int,
    _: dict = Depends(require_role("auditor")),
    db: Session = Depends(get_db),
):
    repo = AIGeneratedContentRepository(db)
    stored = repo.find_by_source("execution", execution_id, content_type="explanation")
    if stored:
        return _to_response(stored)

    exec_repo = ExecutionHistoryRepository(db)
    record = exec_repo.get(execution_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")

    svc = get_groq()
    request_data = record.request_data or {}
    result = svc.explain_decision(
        matched_rule=record.matched_rule,
        decision=record.decision,
        reason=record.reason or "",
        request=request_data,
    )
    if not result["success"]:
        raise HTTPException(status_code=502, detail=result.get("error", "Groq API call failed"))

    _persist(
        db,
        content_type="explanation",
        source_type="execution",
        source_id=execution_id,
        result=result,
        tool=record.tool,
        action=record.action,
        decision=record.decision,
        matched_rule=record.matched_rule,
    )
    stored = repo.find_by_source("execution", execution_id, content_type="explanation")
    return _to_response(stored)


@router.get("/audit/{audit_id}/summary", response_model=AIGeneratedContentResponse)
def get_audit_summary(
    audit_id: int,
    _: dict = Depends(require_role("auditor")),
    db: Session = Depends(get_db),
):
    repo = AIGeneratedContentRepository(db)
    stored = repo.find_by_source("audit", audit_id, content_type="audit_summary")
    if stored:
        return _to_response(stored)

    audit_repo = AuditLogRepository(db)
    record = audit_repo.get(audit_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Audit log {audit_id} not found")

    record_dict = {
        "timestamp": record.timestamp.isoformat() if record.timestamp else None,
        "tool": record.tool,
        "action": record.action,
        "decision": record.decision,
        "matched_rule": record.matched_rule,
        "reason": record.reason,
        "request": record.request_data,
    }

    svc = get_groq()
    result = svc.audit_summary(record=record_dict)
    if not result["success"]:
        raise HTTPException(status_code=502, detail=result.get("error", "Groq API call failed"))

    _persist(
        db,
        content_type="audit_summary",
        source_type="audit",
        source_id=audit_id,
        result=result,
        tool=record.tool,
        action=record.action,
        decision=record.decision,
        matched_rule=record.matched_rule,
    )
    stored = repo.find_by_source("audit", audit_id, content_type="audit_summary")
    return _to_response(stored)


@router.get("/simulation/{simulation_id}/analysis", response_model=AIGeneratedContentResponse)
def get_simulation_analysis(
    simulation_id: int,
    _: dict = Depends(require_role("auditor")),
    db: Session = Depends(get_db),
):
    repo = AIGeneratedContentRepository(db)
    stored = repo.find_by_source("simulation", simulation_id, content_type="simulation_analysis")
    if stored:
        return _to_response(stored)

    sim_repo = SimulationRunRepository(db)
    record = sim_repo.get(simulation_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Simulation run {simulation_id} not found")

    svc = get_groq()
    result = svc.simulation_analysis(
        summary=record.summary,
        results=record.results,
    )
    if not result["success"]:
        raise HTTPException(status_code=502, detail=result.get("error", "Groq API call failed"))

    _persist(
        db,
        content_type="simulation_analysis",
        source_type="simulation",
        source_id=simulation_id,
        result=result,
    )
    stored = repo.find_by_source("simulation", simulation_id, content_type="simulation_analysis")
    return _to_response(stored)


from pydantic import BaseModel
from typing import List, Dict, Any

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None

@router.post("/chat")
def chat_endpoint(
    payload: ChatRequest,
    db: Session = Depends(get_db),
):
    svc = get_groq()
    history_dicts = []
    if payload.history:
        history_dicts = [h.model_dump() for h in payload.history]

    result = svc.run_chat_agent(payload.message, history_dicts)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Groq API call failed"))

    is_tool_call = result.get("is_tool_call", False)
    tool_call = result.get("tool_call")

    execution_result = None
    explanation = None
    recommendations = None
    risk_level = None
    summary = None

    if is_tool_call and tool_call:
        from app.models.request import ActionRequest
        from app.api.routes import execute as execute_action
        try:
            tool_name = tool_call.get("tool")
            action_name = tool_call.get("action")
            extra_params = {}
            if tool_name == "database" and tool_call.get("record_count") is not None:
                extra_params["record_count"] = tool_call["record_count"]
            elif tool_name == "email" and tool_call.get("recipient") is not None:
                extra_params["recipient"] = tool_call["recipient"]
                if tool_call.get("name") is not None:
                    extra_params["name"] = tool_call["name"]
            elif tool_name == "file" and tool_call.get("path") is not None:
                extra_params["path"] = tool_call["path"]

            action_req = ActionRequest(
                tool=tool_name,
                action=action_name,
                **extra_params
            )

            # Call routes.execute directly, passing dry_run=False to prevent Query default behavior
            exec_res = execute_action(request=action_req, dry_run=False, db=db)
            execution_result = exec_res.model_dump()

            decision = execution_result.get("decision")
            reason = execution_result.get("reason", "")
            matched_rule = execution_result.get("matched_rule")

            explain_res = svc.explain_decision(
                matched_rule=matched_rule,
                decision=decision,
                reason=reason,
                request=action_req.model_dump()
            )

            if explain_res.get("success"):
                explanation = explain_res.get("explanation")
                recommendations = explain_res.get("recommendations")
                risk_level = explain_res.get("risk_level")
                summary = explain_res.get("summary")
        except Exception as e:
            logger.exception("Error executing tool from chat agent")
            execution_result = {
                "status": "error",
                "tool_output": {"status": "error", "message": str(e)},
                "decision": "block",
                "reason": f"Execution error: {str(e)}"
            }

    return {
        "response": result.get("response", ""),
        "is_tool_call": is_tool_call,
        "tool_call": tool_call,
        "execution_result": execution_result,
        "explanation": explanation,
        "recommendations": recommendations,
        "risk_level": risk_level,
        "summary": summary
    }
