import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any


class BaseAuditLogger(ABC):
    """Abstract base class for audit loggers."""

    @abstractmethod
    def log(self, request: Dict[str, Any], decision: Dict[str, Any]) -> None:
        """Logs the request and decision details."""
        pass


class FileAuditLogger(BaseAuditLogger):
    """Logs evaluation records to a local JSONL file."""

    def __init__(self, filepath: str = "logs/audit.log"):
        self.filepath = filepath

    def log(self, request: Dict[str, Any], decision: Dict[str, Any]) -> None:
        record = {
            "timestamp": datetime.now().isoformat(),
            "tool": request.get("tool"),
            "action": request.get("action"),
            "request": request,
            "decision": decision.get("decision"),
            "matched_rule": decision.get("matched_rule"),
            "reason": decision.get("reason")
        }

        import os
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, "a") as f:
            f.write(json.dumps(record))
            f.write("\n")


# Alias for backward compatibility
class AuditLogger(FileAuditLogger):
    pass
