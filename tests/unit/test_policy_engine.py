"""Unit tests for the policy loader, policy engine, and Guardrail orchestrator."""

import yaml
import pytest

from app.core.loader import PolicyLoader
from app.core.policy_engine import PolicyEngine
from app.core.guardrail import Guardrail

BASE_POLICIES = {
    "rules": [
        {
            "id": "block_large_delete",
            "tool": "database",
            "action": "delete",
            "conditions": [{"field": "record_count", "operator": ">", "value": 100}],
            "combinator": "AND",
            "decision": "block",
            "message": "Delete request exceeds maximum allowed limit (100 records).",
        },
        {
            "id": "external_email_hitl",
            "tool": "email",
            "action": "send",
            "conditions": [{"field": "external", "operator": "==", "value": True}],
            "combinator": "AND",
            "decision": "require_hitl",
            "message": "External emails require human approval.",
        },
        {
            "id": "confidential_file_log",
            "tool": "file",
            "action": "read",
            "conditions": [{"field": "path", "operator": "contains", "value": "confidential"}],
            "combinator": "AND",
            "decision": "log_and_allow",
            "message": "Confidential file access logged for auditing.",
        },
    ]
}


@pytest.fixture()
def policy_file(tmp_path):
    path = tmp_path / "policies.yaml"
    path.write_text(yaml.safe_dump(BASE_POLICIES))
    return str(path)


@pytest.mark.unit
class TestPolicyLoader:
    def test_loads_rules_from_file(self, policy_file):
        loader = PolicyLoader(policy_file)
        rules = loader.load_rules()
        assert len(rules) == 3
        assert rules[0]["id"] == "block_large_delete"

    def test_default_policy_file_resolves(self):
        # configs/default.yaml exists in the repo and is the default
        loader = PolicyLoader()
        rules = loader.load_rules()
        assert any(r["id"] == "block_large_delete" for r in rules)

    def test_missing_file_raises(self, tmp_path):
        loader = PolicyLoader(str(tmp_path / "does-not-exist.yaml"))
        with pytest.raises(FileNotFoundError):
            loader.load_rules()

    def test_file_without_rules_key_returns_empty(self, tmp_path):
        path = tmp_path / "empty.yaml"
        path.write_text(yaml.safe_dump({"other": "data"}))
        loader = PolicyLoader(str(path))
        assert loader.load_rules() == []


@pytest.mark.unit
class TestPolicyEngine:
    def test_engine_loads_rules(self, policy_file):
        engine = PolicyEngine(policy_file)
        rules = engine.get_rules()
        assert len(rules) == 3

    def test_get_rules_hot_reloads(self, policy_file):
        engine = PolicyEngine(policy_file)
        assert len(engine.get_rules()) == 3

        import copy
        import pathlib

        data = copy.deepcopy(BASE_POLICIES)
        data["rules"].append(
            {
                "id": "new_rule",
                "tool": "database",
                "action": "delete",
                "conditions": [],
                "decision": "block",
                "message": "New rule",
            }
        )
        pathlib.Path(policy_file).write_text(yaml.safe_dump(data))

        rules = engine.get_rules()
        assert any(r["id"] == "new_rule" for r in rules)


@pytest.mark.unit
class TestGuardrail:
    def test_allow_when_no_rule_matches(self, policy_file):
        guardrail = Guardrail(policy_file)
        result = guardrail.evaluate({"tool": "database", "action": "delete", "record_count": 5})
        assert result["decision"] == "allow"
        assert result["matched_rule"] is None

    def test_block_rule_matches(self, policy_file):
        guardrail = Guardrail(policy_file)
        result = guardrail.evaluate({"tool": "database", "action": "delete", "record_count": 500})
        assert result["decision"] == "block"
        assert result["matched_rule"] == "block_large_delete"
        assert "exceeds" in result["reason"]

    def test_require_hitl_rule_matches(self, policy_file):
        guardrail = Guardrail(policy_file)
        result = guardrail.evaluate(
            {"tool": "email", "action": "send", "external": True, "recipient": "x@external.com"}
        )
        assert result["decision"] == "require_hitl"
        assert result["matched_rule"] == "external_email_hitl"

    def test_log_and_allow_rule_matches(self, policy_file):
        guardrail = Guardrail(policy_file)
        result = guardrail.evaluate(
            {"tool": "file", "action": "read", "path": "docs/confidential_salary.pdf"}
        )
        assert result["decision"] == "log_and_allow"
        assert result["matched_rule"] == "confidential_file_log"

    def test_first_match_priority(self, policy_file):
        """First matching rule wins, so an earlier block shadows a later allow."""
        guardrail = Guardrail(policy_file)
        result = guardrail.evaluate({"tool": "database", "action": "delete", "record_count": 500})
        assert result["decision"] == "block"
