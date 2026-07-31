"""Unit tests for OpenTelemetry tracing setup paths."""

import pytest


@pytest.mark.unit
class TestTracing:
    def test_setup_tracing_disabled(self, monkeypatch):
        from app.observability import config as cfg
        import app.observability.tracing as tracing

        monkeypatch.setattr(cfg, "OTEL_ENABLED", False)
        monkeypatch.setattr(tracing, "_configured", False)
        monkeypatch.setattr(tracing, "_tracer", None)

        assert tracing.setup_tracing() is False
        assert tracing.tracing_enabled() is False

    def test_setup_tracing_already_configured(self, monkeypatch):
        import app.observability.tracing as tracing

        monkeypatch.setattr(tracing, "_configured", True)
        assert tracing.setup_tracing() is True

    def test_setup_tracing_enabled(self, monkeypatch):
        from app.observability import config as cfg
        import app.observability.tracing as tracing

        monkeypatch.setattr(cfg, "OTEL_ENABLED", True)
        monkeypatch.setattr(cfg, "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
        monkeypatch.setattr(tracing, "_configured", False)
        monkeypatch.setattr(tracing, "_tracer", None)

        assert tracing.setup_tracing() is True
        assert tracing.tracing_enabled() is True

    def test_setup_tracing_exporter_failure_falls_back_to_noop(self, monkeypatch):
        from app.observability import config as cfg
        import app.observability.tracing as tracing

        monkeypatch.setattr(cfg, "OTEL_ENABLED", True)
        monkeypatch.setattr(tracing, "_configured", False)
        monkeypatch.setattr(tracing, "_tracer", None)

        def fake_import(name, *args, **kwargs):
            if "otlp" in name:
                raise ImportError("exporter not installed")
            return __import__(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", fake_import)

        assert tracing.setup_tracing() is False
        assert tracing.tracing_enabled() is False

    def test_get_tracer_triggers_setup(self, monkeypatch):
        import app.observability.tracing as tracing

        monkeypatch.setattr(tracing, "_tracer", None)
        monkeypatch.setattr(tracing, "setup_tracing", lambda: None)
        assert tracing.get_tracer() is None
