"""Prometheus metrics registry and recording helpers.

Metrics follow the RED/USE production patterns:
- Rate:   http_requests_total, executions_total, security_events_total
- Errors: failures_total, http_requests_total{status=5xx}
- Duration: http_request_duration_seconds, execution_duration_seconds,
            tool_latency_seconds
- Utilisation: active_executions gauge, process/GC collectors
"""

from typing import Optional

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    ProcessCollector,
    gc_collector,
    platform_collector,
)

from app.observability import config

if config.PROMETHEUS_ENABLED:
    REGISTRY = CollectorRegistry()
    _gc = gc_collector.GCCollector(registry=REGISTRY)
    _platform = platform_collector.PlatformCollector(registry=REGISTRY)
    _process = ProcessCollector(registry=REGISTRY)
else:
    REGISTRY = None

NAMESPACE = config.METRICS_NAMESPACE

# --- HTTP layer -----------------------------------------------------------
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests handled",
    ["method", "path", "status"],
    namespace=NAMESPACE,
    registry=REGISTRY,
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    namespace=NAMESPACE,
    registry=REGISTRY,
)

# --- Execution layer ------------------------------------------------------
executions_total = Counter(
    "executions_total",
    "Tool executions by outcome",
    ["tool", "action", "decision", "status"],
    namespace=NAMESPACE,
    registry=REGISTRY,
)
execution_duration_seconds = Histogram(
    "execution_duration_seconds",
    "End-to-end execution time in seconds (policy + tool)",
    ["tool", "action", "decision"],
    namespace=NAMESPACE,
    registry=REGISTRY,
)
tool_latency_seconds = Histogram(
    "tool_latency_seconds",
    "Tool plugin execution latency in seconds",
    ["tool", "action"],
    namespace=NAMESPACE,
    registry=REGISTRY,
)
active_executions = Gauge(
    "active_executions",
    "In-flight tool executions",
    namespace=NAMESPACE,
    registry=REGISTRY,
)

# --- Failure / security layer ---------------------------------------------
failures_total = Counter(
    "failures_total",
    "Failures by component and type",
    ["component", "type"],
    namespace=NAMESPACE,
    registry=REGISTRY,
)
security_events_total = Counter(
    "security_events_total",
    "Security events by event type, severity and outcome",
    ["event", "severity", "outcome"],
    namespace=NAMESPACE,
    registry=REGISTRY,
)

# --- Domain gauges ----------------------------------------------------------
policy_rule_count = Gauge(
    "policy_rule_count",
    "Number of policy rules loaded",
    namespace=NAMESPACE,
    registry=REGISTRY,
)
db_operations_total = Counter(
    "db_operations_total",
    "Database operations by outcome",
    ["operation", "outcome"],
    namespace=NAMESPACE,
    registry=REGISTRY,
)


def record_execution(
    tool: str,
    action: str,
    decision: str,
    status: str,
    total_ms: float,
    tool_latency_ms: Optional[float] = None,
) -> None:
    """Record an executed action against the execution metrics."""
    if not config.PROMETHEUS_ENABLED:
        return
    executions_total.labels(tool, action, decision, status).inc()
    execution_duration_seconds.labels(tool, action, decision).observe(total_ms / 1000.0)
    if tool_latency_ms is not None and tool_latency_ms > 0:
        tool_latency_seconds.labels(tool, action).observe(tool_latency_ms / 1000.0)


def record_failure(component: str, failure_type: str) -> None:
    if not config.PROMETHEUS_ENABLED:
        return
    failures_total.labels(component, failure_type).inc()


def record_security_event(event: str, severity: str, outcome: str) -> None:
    if not config.PROMETHEUS_ENABLED:
        return
    security_events_total.labels(event, severity, outcome).inc()


def record_db_operation(operation: str, outcome: str) -> None:
    if not config.PROMETHEUS_ENABLED:
        return
    db_operations_total.labels(operation, outcome).inc()


def set_policy_rule_count(count: int) -> None:
    if config.PROMETHEUS_ENABLED:
        policy_rule_count.set(count)
