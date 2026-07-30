from fastapi import APIRouter
from typing import List
from app.core.policy_engine import PolicyEngine
from app.core.guardrail import Guardrail
from app.core.executor import ToolExecutor
from app.audit.logger import AuditLogger
from app.simulator.simulation import Simulation
from app.models.request import ActionRequest
from app.models.response import EvaluationResult, ExecutionResult, SimulationResult

router = APIRouter()

policy_engine = PolicyEngine()
guardrail = Guardrail()
executor = ToolExecutor()
audit = AuditLogger()
simulation = Simulation()


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


@router.get("/policies")
def get_policies():
    return {
        "rules": policy_engine.get_rules()
    }


@router.post("/evaluate", response_model=EvaluationResult)
def evaluate(request: ActionRequest):
    req_dict = request.model_dump()
    result = guardrail.evaluate(req_dict)
    return EvaluationResult(**result)


@router.post("/execute", response_model=ExecutionResult)
def execute(request: ActionRequest):
    req_dict = request.model_dump()
    result = guardrail.evaluate(req_dict)

    audit.log(req_dict, result)

    decision = result["decision"]

    if decision == "block":
        return ExecutionResult(
            status="blocked",
            decision=decision,
            matched_rule=result.get("matched_rule"),
            reason=result.get("reason"),
            tool_output={"status": "Blocked by Guardrail"}
        )

    elif decision == "require_hitl":
        return ExecutionResult(
            status="waiting_for_human",
            decision=decision,
            matched_rule=result.get("matched_rule"),
            reason=result.get("reason"),
            tool_output={"status": "Pending Human Approval"}
        )

    else:
        output = executor.execute(req_dict, dry_run=request.dry_run)

        # Handle unsupported tools
        if output.get("status") == "error":
            return ExecutionResult(
                status="failed",
                decision=decision,
                matched_rule=result.get("matched_rule"),
                reason=result.get("reason"),
                tool_output=output
            )

        if decision == "log_and_allow":
            return ExecutionResult(
                status="executed_with_logging",
                decision=decision,
                matched_rule=result.get("matched_rule"),
                reason=result.get("reason"),
                tool_output=output
            )

        return ExecutionResult(
            status="executed",
            decision=decision,
            matched_rule=result.get("matched_rule"),
            reason=result.get("reason"),
            tool_output=output
        )


@router.get("/simulate", response_model=SimulationResult)
def simulate():
    res = simulation.run()
    return SimulationResult(**res)


@router.get("/audit", response_model=List[str])
def get_logs():
    with open("logs/audit.log", "r") as f:
        return f.readlines()
