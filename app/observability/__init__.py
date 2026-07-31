"""Enterprise observability: structured logging, health checks, Prometheus
metrics, OpenTelemetry tracing and security event emission."""

from app.observability import config
from app.observability.logging import (
    JsonLogFormatter,
    get_context,
    get_logger,
    reset_context,
    set_context,
    setup_logging,
)
from app.observability.metrics import (
    REGISTRY,
    active_executions,
    db_operations_total,
    executions_total,
    failures_total,
    http_request_duration_seconds,
    http_requests_total,
    policy_rule_count,
    record_db_operation,
    record_execution,
    record_failure,
    record_security_event,
    security_events_total,
    set_policy_rule_count,
    tool_latency_seconds,
)
from app.observability.middleware import ObservabilityMiddleware
from app.observability.security import emit as emit_security_event
from app.observability.tracing import get_tracer, setup_tracing, tracing_enabled


def setup_observability() -> None:
    """Configure structured logging and (optionally) OpenTelemetry tracing."""
    setup_logging()
    setup_tracing()


__all__ = [
    "config",
    "JsonLogFormatter",
    "get_context",
    "get_logger",
    "reset_context",
    "set_context",
    "setup_logging",
    "setup_observability",
    "setup_tracing",
    "tracing_enabled",
    "get_tracer",
    "ObservabilityMiddleware",
    "emit_security_event",
    "REGISTRY",
    "http_requests_total",
    "http_request_duration_seconds",
    "executions_total",
    "execution_duration_seconds",
    "tool_latency_seconds",
    "active_executions",
    "failures_total",
    "security_events_total",
    "policy_rule_count",
    "db_operations_total",
    "record_execution",
    "record_failure",
    "record_security_event",
    "record_db_operation",
    "set_policy_rule_count",
]
