import yaml
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.database.repositories.policy_repository import PolicyRepository
from app.database.models.policy import PolicyModel
from app.models.policy import (
    PolicyCreate,
    PolicyUpdate,
    PolicyResponse,
    PolicyConflict,
    PolicyValidationResult,
    RulePreviewRequest,
    RulePreviewResult,
)
from app.core.evaluator import PolicyEvaluator
from app.core.operators import compare

VALID_DECISIONS = {"allow", "block", "require_hitl", "log_and_allow"}
VALID_OPERATORS = {">", "<", ">=", "<=", "==", "!=", "contains", "startswith", "endswith"}


def model_to_response(model: PolicyModel) -> PolicyResponse:
    return PolicyResponse(
        id=model.id,
        rule_id=model.rule_id,
        tool=model.tool,
        action=model.action,
        conditions=model.conditions if model.conditions else [],
        combinator=model.combinator,
        decision=model.decision,
        message=model.message,
        priority=model.priority,
        version=model.version,
        enabled=model.enabled,
        tags=model.tags,
        created_at=model.created_at.isoformat() if model.created_at else None,
        updated_at=model.updated_at.isoformat() if model.updated_at else None,
    )


def validate_policy(data: Dict[str, Any]) -> PolicyValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    if not data.get("rule_id"):
        errors.append("rule_id is required")
    if not data.get("tool"):
        errors.append("tool is required")
    if not data.get("action"):
        errors.append("action is required")
    if not data.get("message"):
        errors.append("message is required")

    decision = data.get("decision", "")
    if decision not in VALID_DECISIONS:
        errors.append(f"decision must be one of: {', '.join(sorted(VALID_DECISIONS))}")

    conditions = data.get("conditions", [])
    if not isinstance(conditions, list):
        errors.append("conditions must be a list")
    else:
        for i, cond in enumerate(conditions):
            if not isinstance(cond, dict):
                errors.append(f"condition[{i}] must be an object")
                continue
            if "field" not in cond:
                errors.append(f"condition[{i}] missing required field 'field'")
            if "operator" not in cond:
                errors.append(f"condition[{i}] missing required field 'operator'")
            elif cond.get("operator") not in VALID_OPERATORS:
                warnings.append(
                    f"condition[{i}]: unknown operator '{cond.get('operator')}' - will be validated at runtime"
                )
            if "value" not in cond:
                errors.append(f"condition[{i}] missing required field 'value'")

    combinator = data.get("combinator", "AND")
    if combinator.upper() not in ("AND", "OR"):
        errors.append("combinator must be AND or OR")

    priority = data.get("priority", 0)
    if not isinstance(priority, int) or priority < 0:
        errors.append("priority must be a non-negative integer")

    return PolicyValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def detect_conflicts(
    repo: PolicyRepository,
    tool: str,
    action: str,
    decision: str,
    exclude_rule_id: Optional[str] = None,
) -> List[PolicyConflict]:
    conflicts: List[PolicyConflict] = []
    conflicting = repo.find_conflicts(tool, action, decision, exclude_rule_id)
    for c in conflicting:
        conflicts.append(
            PolicyConflict(
                existing_policy_id=c.id,
                existing_rule_id=c.rule_id,
                field="decision",
                description=(
                    f"Policy '{c.rule_id}' has decision '{c.decision}' "
                    f"on tool={tool} action={action}, "
                    f"while new policy would have '{decision}'. "
                    f"First-match evaluation means one may never trigger."
                ),
            )
        )
    return conflicts


def preview_rule(
    policy_data: Dict[str, Any], request: Dict[str, Any]
) -> RulePreviewResult:
    rule = {
        "id": policy_data.get("rule_id", "preview"),
        "tool": policy_data.get("tool", ""),
        "action": policy_data.get("action", ""),
        "conditions": policy_data.get("conditions", []),
        "combinator": policy_data.get("combinator", "AND"),
        "decision": policy_data.get("decision", "allow"),
        "message": policy_data.get("message", ""),
    }

    evaluator = PolicyEvaluator()
    would_match = evaluator.evaluate_rule(rule, request)

    if not would_match:
        return RulePreviewResult(
            would_match=False,
            decision="N/A",
            message="Policy conditions do not match this request",
            reason="No match",
        )

    return RulePreviewResult(
        would_match=True,
        decision=rule["decision"],
        message=rule["message"],
        reason=f"Request matches policy '{rule['id']}' -> {rule['decision']}: {rule['message']}",
    )


def export_policies(repo: PolicyRepository) -> str:
    models = repo.list_all()
    rules = []
    for m in models:
        rule: Dict[str, Any] = {
            "id": m.rule_id,
            "tool": m.tool,
            "action": m.action,
        }
        if m.conditions:
            rule["conditions"] = m.conditions
        if m.combinator != "AND":
            rule["combinator"] = m.combinator
        rule["decision"] = m.decision
        rule["message"] = m.message
        if m.priority:
            rule["priority"] = m.priority
        if not m.enabled:
            rule["enabled"] = False
        if m.tags:
            rule["tags"] = m.tags
        rules.append(rule)

    return yaml.safe_dump({"rules": rules}, default_flow_style=False, sort_keys=False)


def import_policies(
    repo: PolicyRepository, yaml_content: str
) -> Tuple[int, int, List[str]]:
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}")
    if not data or "rules" not in data:
        raise ValueError("Invalid YAML: must contain 'rules' key")

    rules = data["rules"]
    created = 0
    updated = 0
    errors: List[str] = []

    for rule in rules:
        if "id" not in rule:
            errors.append(f"Skipping rule without 'id': {rule}")
            continue

        rule_id = rule["id"]
        rule_data = {
            "rule_id": rule_id,
            "tool": rule.get("tool", ""),
            "action": rule.get("action", ""),
            "conditions": rule.get("conditions", []),
            "combinator": rule.get("combinator", "AND"),
            "decision": rule.get("decision", ""),
            "message": rule.get("message", ""),
            "priority": rule.get("priority", 0),
            "enabled": rule.get("enabled", True),
            "tags": rule.get("tags"),
        }

        existing = repo.find_by_rule_id(rule_id)
        if existing:
            repo.update_policy(rule_id, rule_data)
            updated += 1
        else:
            repo.create_policy(rule_data)
            created += 1

    repo.session.commit()
    return created, updated, errors
