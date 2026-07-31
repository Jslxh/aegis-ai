from typing import Any, Dict

from sqlalchemy.orm import Session

from app.database.models.execution_history import ExecutionHistoryModel
from app.database.repositories.base import BaseRepository


class ExecutionHistoryRepository(BaseRepository[ExecutionHistoryModel]):
    def __init__(self, session: Session):
        super().__init__(session, ExecutionHistoryModel)

    def create_record(
        self,
        request: Dict[str, Any],
        decision: Dict[str, Any],
        execution_status: str,
        tool_output: Dict[str, Any] | None = None,
        correlation_id: str | None = None,
        request_id: str | None = None,
        execution_id: str | None = None,
    ) -> ExecutionHistoryModel:
        model = ExecutionHistoryModel(
            tool=request.get("tool", ""),
            action=request.get("action", ""),
            request_data=request,
            decision=decision.get("decision", ""),
            matched_rule=decision.get("matched_rule"),
            reason=decision.get("reason"),
            execution_status=execution_status,
            tool_output=tool_output,
            correlation_id=correlation_id,
            request_id=request_id,
            execution_id=execution_id,
        )
        return self.add(model)

    def list_recent(self, limit: int = 50) -> list[ExecutionHistoryModel]:
        return (
            self.session.query(ExecutionHistoryModel)
            .order_by(ExecutionHistoryModel.created_at.desc())
            .limit(limit)
            .all()
        )
