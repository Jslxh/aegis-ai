"""Structured (JSON) logging with request context propagation.

Every log record is enriched with the active request context
(correlation_id, request_id, execution_id, user_id, method, path, ...)
set by the observability middleware, so logs are fully correlatable.
"""

import json
import logging
import sys
import traceback as _traceback
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.observability import config

_request_context: ContextVar[Dict[str, str]] = ContextVar(
    "request_context", default={}
)


def set_context(**kwargs: Any) -> None:
    """Merge key/value pairs into the current request context."""
    current = _request_context.get().copy()
    for key, value in kwargs.items():
        if value is not None:
            current[key] = str(value)
    _request_context.set(current)


def get_context() -> Dict[str, str]:
    return _request_context.get().copy()


def reset_context() -> None:
    _request_context.set({})


_STANDARD_ATTRS = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "taskName",
        "message",
    }
)


class JsonLogFormatter(logging.Formatter):
    """Formats LogRecords as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key in (
            "module",
            "lineno",
            "funcName",
            "threadName",
            "processName",
        ):
            value = getattr(record, key, None)
            if value is not None and key not in payload:
                payload[key] = value

        # Merge active request/execution context.
        payload.update(_request_context.get())

        # Merge user-supplied structured extras (e.g. event, tool, action).
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and key not in payload:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = _traceback.format_exception(
                *record.exc_info
            )

        return json.dumps(payload, default=str, separators=(",", ":"))


def setup_logging(level: Optional[str] = None) -> None:
    """Configure the root logger with a JSON formatter."""
    level = (level or config.LOG_LEVEL).upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    root = logging.getLogger()
    root.setLevel(level)
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    # Uvicorn access logs are replaced by the observability middleware's
    # structured access logging; silence the default access logger.
    logging.getLogger("uvicorn.access").disabled = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
