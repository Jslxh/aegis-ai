"""Unit tests for observability primitives: metrics, security events, health checks, logging."""

import logging
import json

import pytest

from app.observability import config
from app.observability import health
from app.observability import metrics as m
from app.observability.security import emit as emit_security_event
from app.observability.logging import (
    JsonLogFormatter,
    get_context,
    reset_context,
    set_context,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(
        not config.PROMETHEUS_ENABLED, reason="Prometheus metrics disabled"
    ),
]


@pytest.mark.unit
class TestMetricHelpers:
    def test_record_execution_increments_all(self):
        m.executions_total._metrics.clear()
        m.execution_duration_seconds._metrics.clear()
        m.tool_latency_seconds._metrics.clear()

        m.record_execution("database", "delete", "allow", "executed", total_ms=10, tool_latency_ms=5)
        key = ("database", "delete", "allow", "executed")
        assert m.executions_total._metrics[key]._value.get() == 1.0
        assert m.execution_duration_seconds._metrics[("database", "delete", "allow")]._sum.get() == pytest.approx(0.01)
        assert m.tool_latency_seconds._metrics[("database", "delete")]._sum.get() == pytest.approx(0.005)

    def test_record_execution_without_latency(self):
        m.tool_latency_seconds._metrics.clear()
        m.record_execution("database", "delete", "allow", "executed", total_ms=10, tool_latency_ms=None)
        assert m.tool_latency_seconds._metrics.get(("database", "delete")) is None

    def test_record_failure(self):
        m.failures_total._metrics.clear()
        m.record_failure("execution", "tool_error")
        assert m.failures_total._metrics[("execution", "tool_error")]._value.get() == 1.0

    def test_record_security_event(self):
        m.security_events_total._metrics.clear()
        m.record_security_event("security.policy_blocked", "high", "blocked")
        assert m.security_events_total._metrics[("security.policy_blocked", "high", "blocked")]._value.get() == 1.0

    def test_record_db_operation(self):
        m.db_operations_total._metrics.clear()
        m.record_db_operation("execution_history", "success")
        assert m.db_operations_total._metrics[("execution_history", "success")]._value.get() == 1.0

    def test_set_policy_rule_count(self):
        m.set_policy_rule_count(42)
        assert m.policy_rule_count._value.get() == 42.0

    def test_active_executions_gauge(self):
        m.active_executions.inc()
        m.active_executions.inc()
        try:
            assert m.active_executions._value.get() == 2.0
        finally:
            m.active_executions.dec()
            m.active_executions.dec()


@pytest.mark.unit
class TestSecurityEmit:
    def test_emit_increments_metric(self, caplog):
        m.security_events_total._metrics.clear()
        emit_security_event(
            "security.test_event",
            severity="warning",
            outcome="denied",
            username="alice",
            reason="test",
        )
        assert m.security_events_total._metrics[("security.test_event", "warning", "denied")]._value.get() == 1.0

    def test_emit_structured_log_extra(self):
        records = []

        class CaptureHandler(logging.Handler):
            def emit(self, record):
                records.append(record)

        logger = logging.getLogger("guardrail.security")
        handler = CaptureHandler()
        logger.addHandler(handler)
        try:
            emit_security_event("security.test_event", outcome="success", user_id=7)
        finally:
            logger.removeHandler(handler)

        assert len(records) == 1
        assert records[0].__dict__.get("event") == "security.test_event"
        assert records[0].__dict__.get("user_id") == 7

    def test_emit_drops_none_attrs(self):
        records = []

        class CaptureHandler(logging.Handler):
            def emit(self, record):
                records.append(record)

        logger = logging.getLogger("guardrail.security")
        handler = CaptureHandler()
        logger.addHandler(handler)
        try:
            emit_security_event("security.test_event", outcome="success", user_id=None)
        finally:
            logger.removeHandler(handler)

        assert records[0].__dict__.get("user_id") is None


@pytest.mark.unit
class TestHealthChecks:
    def test_liveness(self):
        result = health.liveness()
        assert result["status"] == "ok"
        assert result["service"] == config.SERVICE_NAME

    def test_check_database_ok(self, db_session):
        result = health._check_database(db_session)
        assert result["status"] == "ok"
        assert result["critical"] is True

    def test_check_database_none(self):
        result = health._check_database(None)
        assert result["status"] == "unavailable"

    def test_check_audit_with_db(self):
        assert health._check_audit(object())["channel"] == "postgres"

    def test_check_audit_without_db(self):
        result = health._check_audit(None)
        assert result["channel"] == "file_fallback"
        assert result["status"] == "degraded"

    def test_check_policy_engine_ok(self):
        class FakeEngine:
            def get_rules(self):
                return [1, 2, 3]

        result = health._check_policy_engine(FakeEngine())
        assert result["status"] == "ok"
        assert result["rules"] == 3

    def test_check_policy_engine_none(self):
        result = health._check_policy_engine(None)
        assert result["status"] == "error"

    def test_check_policy_engine_error(self):
        class BrokenEngine:
            def get_rules(self):
                raise RuntimeError("nope")

        result = health._check_policy_engine(BrokenEngine())
        assert result["status"] == "error"

    def test_check_groq_present(self):
        app_state = type("State", (), {"groq_service": object()})()
        assert health._check_groq(app_state)["status"] == "ok"

    def test_check_groq_absent(self):
        app_state = type("State", (), {"groq_service": None})()
        assert health._check_groq(app_state)["status"] == "degraded"

    def test_readiness_all_ok(self, db_session):
        class FakeEngine:
            def get_rules(self):
                return [1]

        app_state = type("State", (), {"groq_service": object()})()
        result = health.readiness(db_session, FakeEngine(), app_state)
        assert result["status"] == "ok"
        assert {c["component"] for c in result["checks"]} == {
            "database", "audit", "policy_engine", "ai",
        }

    def test_readiness_fails_when_db_missing(self):
        result = health.readiness(None, object(), None)
        assert result["status"] == "unavailable"


@pytest.mark.unit
class TestLoggingContext:
    def test_context_set_get_reset(self):
        reset_context()
        set_context(correlation_id="corr_ctx", tool="database")
        ctx = get_context()
        assert ctx["correlation_id"] == "corr_ctx"
        assert ctx["tool"] == "database"
        reset_context()
        assert get_context() == {}

    def test_context_ignores_none_values(self):
        reset_context()
        set_context(correlation_id=None)
        assert get_context() == {}

    def test_json_formatter_produces_valid_json(self):
        logger = logging.getLogger("guardrail.test_formatter")
        logger.setLevel(logging.INFO)
        records = []

        class CaptureHandler(logging.Handler):
            def emit(self, record):
                records.append(record)

        handler = CaptureHandler()
        logger.addHandler(handler)
        formatter = JsonLogFormatter()
        try:
            set_context(correlation_id="corr_json")
            logger.info("hello %s", "world", extra={"event": "custom.event", "user_id": 42})
            line = formatter.format(records[0])
        finally:
            logger.removeHandler(handler)
            reset_context()

        payload = json.loads(line)
        assert payload["message"] == "hello world"
        assert payload["event"] == "custom.event"
        assert payload["user_id"] == 42
        assert payload["correlation_id"] == "corr_json"
        assert "level" in payload
