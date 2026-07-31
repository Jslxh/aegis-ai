"""Unit tests for the policy validation / conflict / preview service layer."""

import pytest

from app.services.policy_service import (
    validate_policy,
    detect_conflicts,
    preview_rule,
    export_policies,
    import_policies,
)

VALID_POLICY = {
    "rule_id": "block_users_table",
    "tool": "database",
    "action": "query",
    "conditions": [{"field": "table", "operator": "==", "value": "users"}],
    "combinator": "AND",
    "decision": "block",
    "message": "Block access to users table",
    "priority": 5,
    "enabled": True,
}


@pytest.mark.unit
class TestValidatePolicy:
    def test_valid_policy(self):
        result = validate_policy(VALID_POLICY)
        assert result.valid is True
        assert result.errors == []

    @pytest.mark.parametrize("field", ["rule_id", "tool", "action", "message"])
    def test_missing_required_field(self, field):
        data = {k: v for k, v in VALID_POLICY.items() if k != field}
        result = validate_policy(data)
        assert result.valid is False
        assert any(field in e for e in result.errors)

    def test_invalid_decision(self):
        data = {**VALID_POLICY, "decision": "maybe"}
        result = validate_policy(data)
        assert result.valid is False
        assert any("decision" in e for e in result.errors)

    def test_conditions_not_list(self):
        data = {**VALID_POLICY, "conditions": "not-a-list"}
        result = validate_policy(data)
        assert result.valid is False

    def test_condition_missing_fields(self):
        data = {**VALID_POLICY, "conditions": [{"field": "table"}]}
        result = validate_policy(data)
        assert result.valid is False
        assert any("operator" in e for e in result.errors)
        assert any("value" in e for e in result.errors)

    def test_unknown_operator_is_warning_not_error(self):
        data = {**VALID_POLICY, "conditions": [{"field": "x", "operator": "regex", "value": "a"}]}
        result = validate_policy(data)
        assert result.valid is True
        assert any("regex" in w for w in result.warnings)

    def test_invalid_combinator(self):
        data = {**VALID_POLICY, "combinator": "XOR"}
        result = validate_policy(data)
        assert result.valid is False

    def test_negative_priority(self):
        data = {**VALID_POLICY, "priority": -1}
        result = validate_policy(data)
        assert result.valid is False


@pytest.mark.unit
class TestPreviewRule:
    def test_preview_matches(self):
        result = preview_rule(VALID_POLICY, {"tool": "database", "action": "query", "table": "users"})
        assert result.would_match is True
        assert result.decision == "block"

    def test_preview_no_match(self):
        result = preview_rule(VALID_POLICY, {"tool": "database", "action": "query", "table": "logs"})
        assert result.would_match is False
        assert result.decision == "N/A"


@pytest.mark.unit
class TestExportImport:
    def test_export_yaml_round_trip(self, db_session):
        from app.database.repositories.policy_repository import PolicyRepository

        repo = PolicyRepository(db_session)
        repo.create_policy(VALID_POLICY)
        db_session.commit()

        yaml_text = export_policies(repo)
        assert "rules:" in yaml_text
        assert VALID_POLICY["rule_id"] in yaml_text

        created, updated, errors = import_policies(repo, yaml_text)
        assert updated == 1
        assert created == 0
        assert errors == []

    def test_import_invalid_yaml_raises(self, db_session):
        from app.database.repositories.policy_repository import PolicyRepository

        repo = PolicyRepository(db_session)
        with pytest.raises(ValueError, match="must contain 'rules'"):
            import_policies(repo, "summary: 'no rules here'")

    def test_import_skips_rule_without_id(self, db_session):
        from app.database.repositories.policy_repository import PolicyRepository

        repo = PolicyRepository(db_session)
        yaml_text = "rules:\n  - tool: database\n    action: delete\n    decision: block\n    message: no id\n"
        created, updated, errors = import_policies(repo, yaml_text)
        assert created == 0
        assert len(errors) == 1
        assert "without 'id'" in errors[0]


@pytest.mark.unit
class TestDetectConflicts:
    def test_conflict_detected(self, db_session):
        from app.database.repositories.policy_repository import PolicyRepository

        repo = PolicyRepository(db_session)
        repo.create_policy(
            {
                **VALID_POLICY,
                "rule_id": "existing_allow",
                "decision": "allow",
            }
        )
        db_session.commit()

        conflicts = detect_conflicts(repo, tool="database", action="query", decision="block")
        assert len(conflicts) == 1
        assert conflicts[0].existing_rule_id == "existing_allow"
        assert "never trigger" in conflicts[0].description

    def test_no_conflict_when_same_decision(self, db_session):
        from app.database.repositories.policy_repository import PolicyRepository

        repo = PolicyRepository(db_session)
        repo.create_policy({**VALID_POLICY, "rule_id": "existing_block"})
        db_session.commit()

        conflicts = detect_conflicts(repo, tool="database", action="query", decision="block")
        assert conflicts == []

    def test_conflict_excludes_own_rule(self, db_session):
        from app.database.repositories.policy_repository import PolicyRepository

        repo = PolicyRepository(db_session)
        repo.create_policy({**VALID_POLICY, "rule_id": "my_rule", "decision": "allow"})
        db_session.commit()

        conflicts = detect_conflicts(
            repo,
            tool="database",
            action="query",
            decision="block",
            exclude_rule_id="my_rule",
        )
        assert conflicts == []
