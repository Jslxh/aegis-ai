from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database.models.policy import PolicyModel
from app.database.repositories.base import BaseRepository


class PolicyRepository(BaseRepository[PolicyModel]):
    def __init__(self, session: Session):
        super().__init__(session, PolicyModel)

    def create_policy(self, data: Dict[str, Any]) -> PolicyModel:
        model = PolicyModel(
            rule_id=data["rule_id"],
            tool=data["tool"],
            action=data["action"],
            conditions=data.get("conditions", []),
            combinator=data.get("combinator", "AND"),
            decision=data["decision"],
            message=data["message"],
            priority=data.get("priority", 0),
            version=1,
            enabled=data.get("enabled", True),
            tags=data.get("tags"),
        )
        return self.add(model)

    def update_policy(self, rule_id: str, data: Dict[str, Any]) -> Optional[PolicyModel]:
        model = (
            self.session.query(PolicyModel)
            .filter(PolicyModel.rule_id == rule_id)
            .first()
        )
        if not model:
            return None

        for field in ("tool", "action", "conditions", "combinator", "decision", "message", "priority", "enabled", "tags"):
            if field in data:
                setattr(model, field, data[field])

        model.version = PolicyModel.version + 1
        self.session.flush()
        return model

    def delete_by_rule_id(self, rule_id: str) -> bool:
        model = (
            self.session.query(PolicyModel)
            .filter(PolicyModel.rule_id == rule_id)
            .first()
        )
        if not model:
            return False
        self.session.delete(model)
        self.session.flush()
        return True

    def find_by_rule_id(self, rule_id: str) -> Optional[PolicyModel]:
        return (
            self.session.query(PolicyModel)
            .filter(PolicyModel.rule_id == rule_id)
            .first()
        )

    def list_all(
        self,
        enabled_only: bool = False,
        tool: Optional[str] = None,
        action: Optional[str] = None,
    ) -> List[PolicyModel]:
        query = self.session.query(PolicyModel)

        if enabled_only:
            query = query.filter(PolicyModel.enabled.is_(True))

        if tool:
            query = query.filter(PolicyModel.tool == tool)

        if action:
            query = query.filter(PolicyModel.action == action)

        return query.order_by(PolicyModel.priority.desc(), PolicyModel.rule_id).all()

    def find_conflicts(
        self, tool: str, action: str, decision: str, exclude_rule_id: Optional[str] = None
    ) -> List[PolicyModel]:
        query = self.session.query(PolicyModel).filter(
            and_(
                PolicyModel.tool == tool,
                PolicyModel.action == action,
                PolicyModel.decision != decision,
                PolicyModel.enabled.is_(True),
            )
        )
        if exclude_rule_id:
            query = query.filter(PolicyModel.rule_id != exclude_rule_id)

        return query.all()

    def upsert_from_rule(self, rule: Dict[str, Any]) -> PolicyModel:
        existing = (
            self.session.query(PolicyModel)
            .filter(PolicyModel.rule_id == rule["id"])
            .first()
        )
        if existing:
            existing.tool = rule.get("tool", existing.tool)
            existing.action = rule.get("action", existing.action)
            existing.conditions = rule.get("conditions", existing.conditions)
            existing.combinator = rule.get("combinator", existing.combinator)
            existing.decision = rule.get("decision", existing.decision)
            existing.message = rule.get("message", existing.message)
            existing.version = PolicyModel.version + 1
            self.session.flush()
            return existing

        model = PolicyModel(
            rule_id=rule["id"],
            tool=rule.get("tool", ""),
            action=rule.get("action", ""),
            conditions=rule.get("conditions", []),
            combinator=rule.get("combinator", "AND"),
            decision=rule.get("decision", ""),
            message=rule.get("message", ""),
            priority=rule.get("priority", 0),
            version=1,
            enabled=rule.get("enabled", True),
            tags=rule.get("tags"),
        )
        return self.add(model)

    def sync_from_yaml(self, rules: List[Dict[str, Any]]) -> None:
        for rule in rules:
            self.upsert_from_rule(rule)
        self.session.commit()

    def find_by_tool_action(self, tool: str, action: str) -> List[PolicyModel]:
        return (
            self.session.query(PolicyModel)
            .filter(PolicyModel.tool == tool, PolicyModel.action == action)
            .all()
        )

    def get_all_rules(self) -> List[Dict[str, Any]]:
        models = self.list()
        return [
            {
                "id": m.rule_id,
                "tool": m.tool,
                "action": m.action,
                "conditions": m.conditions,
                "combinator": m.combinator,
                "decision": m.decision,
                "message": m.message,
            }
            for m in models
        ]

    def count_by_tool_action(self, tool: str, action: str) -> int:
        return (
            self.session.query(PolicyModel)
            .filter(
                and_(
                    PolicyModel.tool == tool,
                    PolicyModel.action == action,
                    PolicyModel.enabled.is_(True),
                )
            )
            .count()
        )
