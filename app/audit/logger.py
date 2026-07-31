import json
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session


class BaseAuditLogger(ABC):
    """Abstract base class for audit loggers."""

    @abstractmethod
    def log(self, request: Dict[str, Any], decision: Dict[str, Any], **context) -> None:
        """Logs the request and decision details."""
        pass


class FileAuditLogger(BaseAuditLogger):
    """Logs evaluation records to a local JSONL file (fallback when DB is unavailable)."""

    def __init__(self, filepath: str = "logs/audit.log"):
        self.filepath = filepath

    def log(self, request: Dict[str, Any], decision: Dict[str, Any], **context) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": request.get("tool"),
            "action": request.get("action"),
            "request": request,
            "decision": decision.get("decision"),
            "matched_rule": decision.get("matched_rule"),
            "reason": decision.get("reason"),
        }
        record.update({k: v for k, v in context.items() if v is not None})

        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, "a") as f:
            f.write(json.dumps(record))
            f.write("\n")


class PostgresAuditLogger(BaseAuditLogger):
    """Logs evaluation records to PostgreSQL via the repository pattern."""

    def __init__(self, session_factory: callable):
        self.session_factory = session_factory

    def log(self, request: Dict[str, Any], decision: Dict[str, Any], **context) -> None:
        from app.database.repositories.audit_log_repository import AuditLogRepository

        session: Session = self.session_factory()
        try:
            repo = AuditLogRepository(session)
            repo.create(request, decision, **context)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# Default to FileAuditLogger for backward compatibility
# PostgresAuditLogger is wired in main.py when DB is available
class AuditLogger(FileAuditLogger):
    pass
