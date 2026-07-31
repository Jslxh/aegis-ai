"""OpenTelemetry tracing setup and span helpers.

Tracing is fully optional: when OpenTelemetry is not configured the SDK
registers a no-op TracerProvider and all instrumentation is a no-op, so the
application remains safe to run without any collector. Configure via:

    OTEL_ENABLED=true
    OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4318
    OTEL_SERVICE_NAME=guardrail-ai
"""

from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

from app.observability import config

_tracer = None
_configured = False


def setup_tracing() -> bool:
    """Initialize the global TracerProvider if OpenTelemetry is enabled."""
    global _tracer, _configured

    if _configured:
        return True

    provider: Optional[TracerProvider] = None
    if config.OTEL_ENABLED:
        resource = Resource.create(
            {
                "service.name": config.OTEL_SERVICE_NAME,
                "service.version": config.SERVICE_VERSION,
            }
        )
        provider = TracerProvider(resource=resource)
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )
            from opentelemetry.sdk.trace.export import (
                BatchSpanProcessor,
            )

            exporter = OTLPSpanExporter(
                endpoint=config.OTEL_EXPORTER_OTLP_ENDPOINT + "/v1/traces"
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except Exception:
            provider = None

    if provider is not None:
        trace.set_tracer_provider(provider)
        _configured = True
    else:
        trace.set_tracer_provider(trace.NoOpTracerProvider())

    _tracer = trace.get_tracer(config.OTEL_SERVICE_NAME)
    return _configured


def get_tracer():
    """Return the application tracer (no-op when tracing is disabled)."""
    global _tracer
    if _tracer is None:
        setup_tracing()
    return _tracer


def tracing_enabled() -> bool:
    return _configured
