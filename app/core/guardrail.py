from typing import Dict, Any
from .policy_engine import PolicyEngine
from .evaluator import PolicyEvaluator


class Guardrail:
    """Orchestrates action guardrail checking logic."""

    def __init__(self, policy_file: str = None):
        self.engine = PolicyEngine(policy_file)
        self.evaluator = PolicyEvaluator()

    def evaluate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        rules = self.engine.get_rules()

        for rule in rules:
            if self.evaluator.evaluate_rule(rule, request):
                return {
                    "decision": rule["decision"],
                    "matched_rule": rule["id"],
                    "reason": rule["message"]
                }

        return {
            "decision": "allow",
            "matched_rule": None,
            "reason": "No matching policy. Action allowed."
        }
