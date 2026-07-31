import os


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_JSON: bool = _bool_env("LOG_JSON", True)

# OpenTelemetry: enabled when OTEL_ENABLED=true or an OTLP endpoint is set.
OTEL_ENABLED: bool = _bool_env("OTEL_ENABLED", False)
OTEL_EXPORTER_OTLP_ENDPOINT: str = os.getenv(
    "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318"
)
OTEL_SERVICE_NAME: str = os.getenv("OTEL_SERVICE_NAME", "guardrail-ai")
OTEL_ENABLED = OTEL_ENABLED or bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))

SERVICE_NAME: str = OTEL_SERVICE_NAME
SERVICE_VERSION: str = os.getenv("SERVICE_VERSION", "1.0.0")

# Prometheus
PROMETHEUS_ENABLED: bool = _bool_env("PROMETHEUS_ENABLED", True)
METRICS_NAMESPACE: str = os.getenv("METRICS_NAMESPACE", "guardrail")

# Trace header used to propagate correlation IDs between services.
CORRELATION_HEADER: str = os.getenv("CORRELATION_HEADER", "X-Correlation-ID")
