import logging
from fastapi import FastAPI
from app.api.routes import router
from app.api import ai_routes
from app.api.auth_routes import router as auth_router
from app.api.monitoring_routes import router as monitoring_router
from app.api.analytics_routes import router as analytics_router
from app.api.audit_routes import router as audit_router
from app.api.approval_routes import router as approval_router
from app.api.observability_routes import router as observability_router
from app.hitl.approval import PgApprovalQueue
from app.core.policy_engine import PolicyEngine
from app.core.guardrail import Guardrail
from app.core.executor import ToolExecutor
from app.audit.logger import AuditLogger, PostgresAuditLogger
from app.simulator.simulation import Simulation
from app.services.groq_service import GroqService
from app.database.session import engine, SessionLocal, Base
from app.database.models import (
    PolicyModel,
    AuditLogModel,
    HITLRequestModel,
    SimulationRunModel,
    ExecutionHistoryModel,
    UserModel,
    RefreshTokenModel,
    RuntimeMetricModel,
    AnalyticsReportModel,
    AIGeneratedContentModel,
)
from app.database.repositories.policy_repository import PolicyRepository
from app.observability import setup_observability, ObservabilityMiddleware
from app.observability.metrics import set_policy_rule_count

setup_observability()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Guardrail AI",
    description="Runtime Guardrails & Policy Enforcement Platform",
    version="1.0.0"
)

app.add_middleware(ObservabilityMiddleware)

app.include_router(router)
app.include_router(ai_routes.router)
app.include_router(auth_router)
app.include_router(monitoring_router)
app.include_router(analytics_router)
app.include_router(audit_router)
app.include_router(approval_router)
app.include_router(observability_router)

# Instantiate managers to retain backward compatibility with direct imports
policy_engine = PolicyEngine()
guardrail = Guardrail()
executor = ToolExecutor()
audit = AuditLogger()
simulation = Simulation()

# Initialize Groq service and inject into ai_routes module
try:
    groq_service = GroqService()
    app.state.groq_service = groq_service
    ai_routes.groq = groq_service
    logger.info("Groq service initialized successfully")
except ValueError as e:
    logger.warning("Groq service not initialized: %s. AI endpoints will return 503.", e)


@app.on_event("startup")
def on_startup():
    """Initialize database and sync policies on application startup."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

        session = SessionLocal()
        try:
            repo = PolicyRepository(session)
            rules = policy_engine.get_rules()
            if rules:
                repo.sync_from_yaml(rules)
                logger.info("Synced %d policies from YAML to database", len(rules))
            set_policy_rule_count(len(rules))
        finally:
            session.close()

        session_factory = lambda: SessionLocal()

        # Wire PostgresAuditLogger into api routes
        import app.api.routes as api_routes_mod
        api_routes_mod.audit = PostgresAuditLogger(session_factory)

        # Wire PostgreSQL-backed approval queue into api routes
        api_routes_mod.approval_queue = PgApprovalQueue(session_factory)

        # Wire session_factory into simulation
        import app.simulator.simulation as sim_mod
        api_routes_mod.simulation = Simulation(session_factory=session_factory)

        app.state.session_factory = session_factory
        logger.info("PostgreSQL persistence layer initialized")

    except Exception as e:
        logger.warning(
            "Database initialization failed: %s. "
            "Falling back to JSONL audit logging and in-memory storage.",
            e,
        )


__all__ = ["app", "policy_engine", "guardrail", "executor", "audit", "simulation"]
