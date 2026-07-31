from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database.models.ai_content import AIGeneratedContentModel
from app.database.repositories.base import BaseRepository


class AIGeneratedContentRepository(BaseRepository[AIGeneratedContentModel]):
    def __init__(self, session: Session):
        super().__init__(session, AIGeneratedContentModel)

    def create_content(
        self,
        content_type: str,
        source_type: str,
        source_id: int,
        tool: Optional[str] = None,
        action: Optional[str] = None,
        decision: Optional[str] = None,
        matched_rule: Optional[str] = None,
        explanation: Optional[str] = None,
        risk_analysis: Optional[str] = None,
        risk_level: Optional[str] = None,
        recommendations: Optional[List[str]] = None,
        confidence: Optional[float] = None,
        summary: Optional[str] = None,
        model: Optional[str] = None,
        latency_ms: Optional[float] = None,
    ) -> AIGeneratedContentModel:
        model = AIGeneratedContentModel(
            content_type=content_type,
            source_type=source_type,
            source_id=source_id,
            tool=tool,
            action=action,
            decision=decision,
            matched_rule=matched_rule,
            explanation=explanation,
            risk_analysis=risk_analysis,
            risk_level=risk_level,
            recommendations=recommendations,
            confidence=confidence,
            summary=summary,
            model=model,
            latency_ms=latency_ms,
        )
        return self.add(model)

    def find_by_source(
        self,
        source_type: str,
        source_id: int,
        content_type: Optional[str] = None,
    ) -> Optional[AIGeneratedContentModel]:
        q = self.session.query(AIGeneratedContentModel).filter(
            AIGeneratedContentModel.source_type == source_type,
            AIGeneratedContentModel.source_id == source_id,
        )
        if content_type:
            q = q.filter(AIGeneratedContentModel.content_type == content_type)
        return q.order_by(AIGeneratedContentModel.created_at.desc()).first()

    def list_by_source(
        self,
        source_type: str,
        source_id: int,
        limit: int = 20,
    ) -> List[AIGeneratedContentModel]:
        return (
            self.session.query(AIGeneratedContentModel)
            .filter(
                AIGeneratedContentModel.source_type == source_type,
                AIGeneratedContentModel.source_id == source_id,
            )
            .order_by(AIGeneratedContentModel.created_at.desc())
            .limit(limit)
            .all()
        )
