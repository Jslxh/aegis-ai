from typing import Any


def compare(request_value: Any, operator: str, rule_value: Any) -> bool:
    """
    Compares request_value and rule_value using the specified comparison operator.
    Supports: >, <, >=, <=, ==, !=, contains, startswith, endswith.
    """
    if isinstance(request_value, (int, float)) and not isinstance(rule_value, (int, float)):
        try:
            rule_value = type(request_value)(rule_value)
        except (ValueError, TypeError):
            pass

    if operator == ">":
        return request_value > rule_value
    elif operator == "<":
        return request_value < rule_value
    elif operator == ">=":
        return request_value >= rule_value
    elif operator == "<=":
        return request_value <= rule_value
    elif operator == "==":
        return request_value == rule_value
    elif operator == "!=":
        return request_value != rule_value
    elif operator == "contains":
        return str(rule_value) in str(request_value)
    elif operator == "startswith":
        return str(request_value).startswith(str(rule_value))
    elif operator == "endswith":
        return str(request_value).endswith(str(rule_value))
    else:
        raise ValueError(f"Unsupported operator: {operator}")
