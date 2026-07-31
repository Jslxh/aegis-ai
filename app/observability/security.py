"""Security event emission: structured logs + Prometheus counters.

All security-relevant actions (auth, RBAC, policy changes, blocks, HITL)
emit a structured event with a shared schema so SIEM tooling can consume a
single, consistent feed:

    {"event": "security.login_failure", "severity": "warning",
     "outcome": "failure", "username": "...", "reason": "...", ...}
"""

import logging
from typing import Any, Dict, Optional

from app.observability.metrics import record_security_event
from app.observability.logging import get_logger

# Event names
LOGIN_SUCCESS = "security.login_success"
LOGIN_FAILURE = "security.login_failure"
REGISTER_USER = "security.user_registered"
LOGOUT = "security.logout"
TOKEN_REFRESH = "security.token_refresh"
RBAC_DENIED = "security.rbac_denied"
POLICY_CREATED = "security.policy_created"
POLICY_UPDATED = "security.policy_updated"
POLICY_DELETED = "security.policy_deleted"
POLICY_BLOCKED = "security.policy_blocked"
HITL_APPROVED = "security.hitl_approved"
HITL_DENIED = "security.hitl_denied"
AUDIT_VERIFY_FAILED = "security.audit_integrity_failed"
TOKEN_REVOKED = "security.token_revoked"

_SEVERITY_LEVEL = {
    "info": logging.INFO,
    "warning": logging.WARNING,
    "high": logging.ERROR,
    "critical": logging.CRITICAL,
}

_logger = get_logger("guardrail.security")


def emit(
    event: str,
    severity: str = "info",
    outcome: str = "success",
    **attrs: Any,
) -> None:
    """Emit a security event to the structured log and Prometheus."""
    record_security_event(event, severity, outcome)
    payload: Dict[str, Any] = {"event": event, "severity": severity, "outcome": outcome}
    payload.update({k: v for k, v in attrs.items() if v is not None})
    _logger.log(
        _SEVERITY_LEVEL.get(severity, logging.INFO),
        "security event",
        extra=payload,
    )
