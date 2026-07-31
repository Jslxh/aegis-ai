"""Unit tests for the PolicyEvaluator."""

import pytest

from app.core.evaluator import PolicyEvaluator

RULES = {
    "block_large_delete": {
        "id": "block_large_delete",
        "tool": "database",
        "action": "delete",
        "conditions": [{"field": "record_count", "operator": ">", "value": 100}],
        "combinator": "AND",
        "decision": "block",
        "message": "Too large",
    },
    "external_email": {
        "id": "external_email",
        "tool": "email",
        "action": "send",
        "conditions": [{"field": "external", "operator": "==", "value": True}],
        "combinator": "AND",
        "decision": "require_hitl",
        "message": "Approval needed",
    },
    "or_combo": {
        "id": "or_combo",
        "tool": "database",
        "action": "query",
        "conditions": [
            {"field": "table", "operator": "==", "value": "users"},
            {"field": "table", "operator": "==", "value": "payments"},
        ],
        "combinator": "OR",
        "decision": "block",
        "message": "Sensitive table",
    },
}


@pytest.mark.unit
class TestEvaluateRule:
    def setup_method(self):
        self.evaluator = PolicyEvaluator()

    def test_tool_mismatch_returns_false(self):
        assert (
            self.evaluator.evaluate_rule(
                RULES["block_large_delete"], {"tool": "email", "action": "delete", "record_count": 500}
            )
            is False
        )

    def test_action_mismatch_returns_false(self):
        assert (
            self.evaluator.evaluate_rule(
                RULES["block_large_delete"], {"tool": "database", "action": "truncate", "record_count": 500}
            )
            is False
        )

    def test_matches_block_rule(self):
        assert (
            self.evaluator.evaluate_rule(
                RULES["block_large_delete"], {"tool": "database", "action": "delete", "record_count": 500}
            )
            is True
        )

    def test_does_not_match_block_rule(self):
        assert (
            self.evaluator.evaluate_rule(
                RULES["block_large_delete"], {"tool": "database", "action": "delete", "record_count": 5}
            )
            is False
        )

    def test_bool_condition(self):
        assert (
            self.evaluator.evaluate_rule(
                RULES["external_email"], {"tool": "email", "action": "send", "external": True}
            )
            is True
        )

    def test_or_combinator(self):
        assert (
            self.evaluator.evaluate_rule(
                RULES["or_combo"], {"tool": "database", "action": "query", "table": "users"}
            )
            is True
        )
        assert (
            self.evaluator.evaluate_rule(
                RULES["or_combo"], {"tool": "database", "action": "query", "table": "logs"}
            )
            is False
        )


@pytest.mark.unit
class TestEvaluateConditions:
    def setup_method(self):
        self.evaluator = PolicyEvaluator()

    def test_empty_conditions_is_true(self):
        assert self.evaluator.evaluate_conditions({"a": 1}, []) is True

    def test_missing_field_counts_as_false(self):
        conditions = [{"field": "missing", "operator": "==", "value": 1}]
        assert self.evaluator.evaluate_conditions({"a": 1}, conditions) is False

    def test_all_conditions_required_for_and(self):
        conditions = [
            {"field": "a", "operator": ">", "value": 1},
            {"field": "b", "operator": "<", "value": 10},
        ]
        assert self.evaluator.evaluate_conditions({"a": 5, "b": 3}, conditions) is True
        assert self.evaluator.evaluate_conditions({"a": 0, "b": 3}, conditions) is False

    def test_any_condition_for_or(self):
        conditions = [
            {"field": "a", "operator": ">", "value": 1},
            {"field": "b", "operator": "<", "value": 10},
        ]
        assert self.evaluator.evaluate_conditions({"a": 0, "b": 3}, conditions, combinator="OR") is True
        assert self.evaluator.evaluate_conditions({"a": 0, "b": 50}, conditions, combinator="OR") is False

    def test_lowercase_or_combinator(self):
        conditions = [{"field": "a", "operator": "==", "value": 1}]
        assert self.evaluator.evaluate_conditions({"a": 1}, conditions, combinator="or") is True
