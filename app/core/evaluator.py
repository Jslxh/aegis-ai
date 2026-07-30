from typing import Any, Dict, List
from app.core.operators import compare


class PolicyEvaluator:
    """Evaluates requests against declarative conditions."""

    def evaluate_rule(self, rule: Dict[str, Any], request: Dict[str, Any]) -> bool:
        """
        Evaluates a single rule against a request.
        """
        if rule.get("tool") != request.get("tool") or rule.get("action") != request.get("action"):
            return False

        conditions = rule.get("conditions", [])
        combinator = rule.get("combinator", "AND")
        return self.evaluate_conditions(request, conditions, combinator=combinator)

    def evaluate_conditions(self, request: Dict[str, Any], conditions: List[Dict[str, Any]], combinator: str = "AND") -> bool:
        """
        Evaluates conditions with support for combinator logic.
        """
        if not conditions:
            return True

        results = []
        for cond in conditions:
            field = cond.get("field")
            operator = cond.get("operator")
            rule_value = cond.get("value")

            if field not in request:
                results.append(False)
                continue

            request_value = request[field]
            results.append(compare(request_value, operator, rule_value))

        if combinator.upper() == "OR":
            return any(results)
        return all(results)
