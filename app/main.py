from fastapi import FastAPI
from app.api.routes import router
from app.core.policy_engine import PolicyEngine
from app.core.guardrail import Guardrail
from app.core.executor import ToolExecutor
from app.audit.logger import AuditLogger
from app.simulator.simulation import Simulation

app = FastAPI(
    title="Guardrail AI",
    description="Runtime Guardrails & Policy Enforcement Platform",
    version="1.0.0"
)

app.include_router(router)

# Instantiate managers to retain backward compatibility with direct imports
policy_engine = PolicyEngine()
guardrail = Guardrail()
executor = ToolExecutor()
audit = AuditLogger()
simulation = Simulation()

__all__ = ["app", "policy_engine", "guardrail", "executor", "audit", "simulation"]
