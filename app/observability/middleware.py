"""ASGI middleware: request tracing, latency metrics and structured access logs."""

import time
import uuid
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode

from app.observability import config
from app.observability.logging import get_logger, reset_context, set_context
from app.observability.metrics import (
    http_request_duration_seconds,
    http_requests_total,
    record_failure,
)
from app.observability.tracing import get_tracer

_logger = get_logger("guardrail.http")

_NO_SPAN_PATHS = {"/metrics", "/health/live", "/health/ready"}


def _generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Adds trace IDs, structured access logs, latency metrics and OTel spans."""

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get(
            config.CORRELATION_HEADER
        ) or _generate_id("corr")
        request_id = _generate_id("req")

        set_context(correlation_id=correlation_id, request_id=request_id)
        request.state.correlation_id = correlation_id
        request.state.request_id = request_id

        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        start = time.monotonic()

        span = None
        tracer = get_tracer()
        if path not in _NO_SPAN_PATHS:
            span = tracer.start_span(
                "http.server.request",
                kind=SpanKind.SERVER,
                attributes={
                    "http.request.method": method,
                    "url.path": path,
                    "server.port": request.url.port or 8000,
                    "client.address": client_ip or "",
                    "user_agent.original": user_agent or "",
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                },
            )
            span_context = trace.set_span_in_context(span)
        else:
            span_context = None

        status_code = 500
        response_size: Optional[int] = None
        exception = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            content_length = response.headers.get("content-length")
            response_size = int(content_length) if content_length else None
        except Exception as exc:  # noqa: BLE001
            exception = exc
            record_failure("http", "unhandled_exception")
            if span is not None:
                span.record_exception(exc)
            raise
        finally:
            duration_ms = (time.monotonic() - start) * 1000

            if span is not None:
                span.set_attribute("http.response.status_code", status_code)
                span.set_attribute("request.duration_ms", round(duration_ms, 2))
                if exception is not None:
                    span.set_status(Status(StatusCode.ERROR, str(exception)))
                else:
                    span.set_status(StatusCode.OK if status_code < 500 else StatusCode.ERROR)
                if span_context is not None:
                    span.end()
                    span = None

            http_requests_total.labels(method, path, str(status_code)).inc()
            http_request_duration_seconds.labels(method, path).observe(duration_ms / 1000.0)

            _log_access(
                method=method,
                path=path,
                status=status_code,
                duration_ms=duration_ms,
                correlation_id=correlation_id,
                request_id=request_id,
                client_ip=client_ip,
                user_agent=user_agent,
                response_size=response_size,
            )

            reset_context()

        return response


def _log_access(
    method: str,
    path: str,
    status: int,
    duration_ms: float,
    correlation_id: str,
    request_id: str,
    client_ip: Optional[str],
    user_agent: Optional[str],
    response_size: Optional[int],
) -> None:
    _logger.info(
        "request completed",
        extra={
            "event": "http.request",
            "method": method,
            "path": path,
            "status": status,
            "duration_ms": round(duration_ms, 2),
            "correlation_id": correlation_id,
            "request_id": request_id,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "response_size": response_size,
        },
    )
