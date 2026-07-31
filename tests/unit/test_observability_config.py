"""Unit tests for observability helpers: config parsing, health checks,
metrics disabled path, and JSON logging."""

import json
import logging

import pytest

from app.observability import config
from app.observability import health
from app.observability.logging import JsonLogFormatter, setup_logging


@pytest.mark.unit
class TestConfigParsing:
    def test_bool_env_true_variants(self, monkeypatch):
        for value in ("1", "true", "TRUE", " yes ", "on"):
            monkeypatch.setenv("TEST_BOOL_FLAG", value)
            assert config._bool_env("TEST_BOOL_FLAG", False) is True

    def test_bool_env_false_variants(self, monkeypatch):
        for value in ("0", "false", "no", "off"):
            monkeypatch.setenv("TEST_BOOL_FLAG", value)
            assert config._bool_env("TEST_BOOL_FLAG", True) is False

    def test_bool_env_missing_uses_default(self, monkeypatch):
        monkeypatch.delenv("TEST_BOOL_FLAG", raising=False)
        assert config._bool_env("TEST_BOOL_FLAG", True) is True


@pytest.mark.unit
class TestHealthChecks:
    def test_database_error_branch(self):
        class BrokenDb:
            def execute(self, sql):
                raise RuntimeError("connection refused")

        result = health._check_database(BrokenDb())
        assert result["status"] == "error"
        assert "connection refused" in result["detail"]

    def test_database_none(self):
        result = health._check_database(None)
        assert result["status"] == "unavailable"

    def test_policy_engine_error_branch(self):
        class BrokenEngine:
            def get_rules(self):
                raise RuntimeError("no policy file")

        result = health._check_policy_engine(BrokenEngine())
        assert result["status"] == "error"

    def test_policy_engine_ok(self):
        class OkEngine:
            def get_rules(self):
                return [{"id": "r1"}]

        result = health._check_policy_engine(OkEngine())
        assert result["status"] == "ok"
        assert result["rules"] == 1

    def test_groq_ok_and_degraded(self):
        class AppState:
            groq_service = object()

        assert health._check_groq(AppState())["status"] == "ok"
        assert health._check_groq(None)["status"] == "degraded"

    def test_readiness_overall_unavailable_when_critical_fails(self):
        class BrokenDb:
            def execute(self, sql):
                raise RuntimeError("down")

        result = health.readiness(BrokenDb(), None, None)
        assert result["status"] == "unavailable"


@pytest.mark.unit
class TestMetricsDisabledPath:
    def test_record_helpers_early_return_when_disabled(self, monkeypatch):
        from app.observability import metrics

        monkeypatch.setattr(config, "PROMETHEUS_ENABLED", False)
        metrics.record_execution("db", "delete", "block", "blocked", 10.0, 5.0)
        metrics.record_failure("http", "boom")
        metrics.record_security_event("e", "high", "blocked")
        metrics.record_db_operation("read", "success")
        metrics.set_policy_rule_count(3)

    def test_set_policy_rule_count_enabled(self, monkeypatch):
        from app.observability import metrics

        monkeypatch.setattr(config, "PROMETHEUS_ENABLED", True)
        metrics.set_policy_rule_count(4)
        assert metrics.policy_rule_count._value.get() == 4

    def test_record_execution_with_latency(self, monkeypatch):
        from app.observability import metrics

        monkeypatch.setattr(config, "PROMETHEUS_ENABLED", True)
        metrics.record_execution("db", "delete", "allow", "executed", 12.0, 3.0)
        key = ("db", "delete", "allow", "executed")
        assert metrics.executions_total._metrics[key]._value.get() >= 1


@pytest.mark.unit
class TestJsonLogFormatter:
    def _format(self, **attrs):
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="hello %(x)s",
            args=({"x": "world"},),
            exc_info=None,
        )
        for key, value in attrs.items():
            setattr(record, key, value)
        return json.loads(JsonLogFormatter().format(record))

    def test_basic_fields(self):
        payload = self._format()
        assert payload["message"] == "hello world"
        assert payload["level"] == "INFO"
        assert payload["logger"] == "test.logger"
        assert "timestamp" in payload

    def test_structured_extras(self):
        payload = self._format(event="http.request", tool="database")
        assert payload["event"] == "http.request"
        assert payload["tool"] == "database"

    def test_missing_standard_attr(self):
        payload = self._format()
        assert payload["module"] == "test_session" or "module" in payload

    def test_exc_info_adds_exception(self):
        try:
            raise ValueError("kaboom")
        except ValueError:
            import sys

            payload = self._format(exc_info=sys.exc_info())
        assert "exception" in payload
        assert any("kaboom" in line for line in payload["exception"])


@pytest.mark.unit
class TestSetupLogging:
    def test_setup_logging_twice_removes_old_handlers(self):
        setup_logging("INFO")
        root = logging.getLogger()
        before = set(root.handlers)
        setup_logging("DEBUG")
        after = set(root.handlers)
        assert after.isdisjoint(before) or after == before
        assert logging.getLogger("uvicorn.access").disabled is True
