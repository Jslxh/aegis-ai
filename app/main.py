from fastapi import FastAPI, Body
import json

from app.policy_engine import PolicyEngine
from app.guardrail import Guardrail
from app.executor import ToolExecutor
from app.audit import AuditLogger
from app.simulation import Simulation

app = FastAPI(
    title="Guardrail AI",
    description="Runtime Guardrails & Policy Enforcement Platform",
    version="1.0.0"
)

policy_engine = PolicyEngine()
guardrail = Guardrail()
executor = ToolExecutor()
audit = AuditLogger()
simulation = Simulation()


@app.get("/")
def root():
    return {
        "message": "Welcome to Guardrail AI"
    }


@app.get("/about")
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


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.get("/policies")
def get_policies():
    return {
        "rules": policy_engine.get_rules()
    }


@app.post("/evaluate")
def evaluate(request: dict = Body(...)):
    return guardrail.evaluate(request)


@app.post("/execute")
def execute(request: dict = Body(...)):

    dry_run = request.get("dry_run", False)

    result = guardrail.evaluate(request)

    audit.log(request, result)

    decision = result["decision"]

    # BLOCK
    if decision == "block":
        return {
            "status": "blocked",
            **result
        }

    # REQUIRE HUMAN APPROVAL
    elif decision == "require_hitl":
        return {
            "status": "waiting_for_human",
            **result
        }

    # ALLOW / LOG & ALLOW
    else:

        output = executor.execute(
            request,
            dry_run=dry_run
        )

        # Handle unsupported tools
        if output.get("status") == "error":
            return {
                "status": "failed",
                **result,
                "tool_output": output
            }

        # LOG & ALLOW
        if decision == "log_and_allow":
            return {
                "status": "executed_with_logging",
                **result,
                "tool_output": output
            }

        # NORMAL ALLOW
        return {
            "status": "executed",
            **result,
            "tool_output": output
        }

@app.get("/simulate")
def simulate():
    return simulation.run()


@app.get("/audit")
def get_logs(): 
    with open("logs/audit.log") as f: 
        return f.readlines()