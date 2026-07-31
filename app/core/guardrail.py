from typing import Dict, Any
from .policy_engine import PolicyEngine
from .evaluator import PolicyEvaluator


class Guardrail:
    """Orchestrates action guardrail checking logic."""

    def __init__(self, policy_file: str = None):
        self.engine = PolicyEngine(policy_file)
        self.evaluator = PolicyEvaluator()

    def evaluate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        # Enrich request with external status if recipient is present
        if request.get("tool") == "email" and request.get("action") == "send" and "recipient" in request:
            import os
            internal_domain = os.getenv("INTERNAL_DOMAIN", "@company.com")
            if not internal_domain.startswith("@"):
                internal_domain = "@" + internal_domain
            recipient = request.get("recipient")
            if recipient and not recipient.lower().endswith(internal_domain.lower()):
                request["external"] = True
            else:
                request["external"] = False

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
