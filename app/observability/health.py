"""Liveness and readiness checks for the /health endpoints."""

import time
from typing import Any, Dict, List, Optional

from app.observability.metrics import record_failure
from app.observability import config


def liveness() -> Dict[str, Any]:
    """Process-level liveness: always healthy while the process is running."""
    return {
        "status": "ok",
        "service": config.SERVICE_NAME,
        "version": config.SERVICE_VERSION,
    }


def _check_database(db: Optional[Any]) -> Dict[str, Any]:
    start = time.monotonic()
    if db is None:
        record_failure("health", "database_unavailable")
        return {
            "component": "database",
            "status": "unavailable",
            "critical": True,
        }
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        return {
            "component": "database",
            "status": "ok",
            "latency_ms": round((time.monotonic() - start) * 1000, 2),
            "critical": True,
        }
    except Exception as e:  # noqa: BLE001
        record_failure("health", "database_error")
        return {
            "component": "database",
            "status": "error",
            "detail": str(e)[:200],
            "critical": True,
        }


def _check_audit(db: Optional[Any]) -> Dict[str, Any]:
    """Audit channel is critical: DB-backed when available, file fallback degrades it."""
    if db is not None:
        return {
            "component": "audit",
            "status": "ok",
            "channel": "postgres",
            "critical": True,
        }
    return {
        "component": "audit",
        "status": "degraded",
        "channel": "file_fallback",
        "detail": "PostgreSQL unavailable; audit records written to JSONL file",
        "critical": True,
    }


def _check_policy_engine(policy_engine: Optional[Any]) -> Dict[str, Any]:
    if policy_engine is None:
        record_failure("health", "policy_engine_unavailable")
        return {
            "component": "policy_engine",
            "status": "error",
            "critical": True,
        }
    try:
        rules = policy_engine.get_rules()
        return {
            "component": "policy_engine",
            "status": "ok",
            "rules": len(rules),
            "critical": True,
        }
    except Exception as e:  # noqa: BLE001
        record_failure("health", "policy_engine_error")
        return {
            "component": "policy_engine",
            "status": "error",
            "detail": str(e)[:200],
            "critical": True,
        }


def _check_groq(app_state: Optional[Any]) -> Dict[str, Any]:
    if app_state is not None and getattr(app_state, "groq_service", None) is not None:
        return {"component": "ai", "status": "ok", "critical": False}
    return {
        "component": "ai",
        "status": "degraded",
        "detail": "Groq service not initialized (check API key)",
        "critical": False,
    }


def readiness(
    db: Optional[Any],
    policy_engine: Optional[Any],
    app_state: Optional[Any],
) -> Dict[str, Any]:
    """Readiness: overall healthy only when all critical components pass."""
    checks: List[Dict[str, Any]] = [
        _check_database(db),
        _check_audit(db),
        _check_policy_engine(policy_engine),
        _check_groq(app_state),
    ]

    critical_failed = any(
        c["critical"] and c["status"] != "ok" for c in checks
    )

    overall = "ok" if not critical_failed else "unavailable"
    return {
        "status": overall,
        "service": config.SERVICE_NAME,
        "version": config.SERVICE_VERSION,
        "checks": checks,
    }
