"""Repository tests for PolicyRepository."""

import pytest

from app.database.repositories.policy_repository import PolicyRepository

VALID_POLICY = {
    "rule_id": "block_large_delete",
    "tool": "database",
    "action": "delete",
    "conditions": [{"field": "record_count", "operator": ">", "value": 100}],
    "combinator": "AND",
    "decision": "block",
    "message": "Delete too large.",
    "priority": 10,
}


@pytest.mark.repo
class TestPolicyRepository:
    def test_create_and_find(self, db_session):
        repo = PolicyRepository(db_session)
        model = repo.create_policy(VALID_POLICY)
        db_session.commit()
        assert model.rule_id == "block_large_delete"
        assert model.version == 1

        found = repo.find_by_rule_id("block_large_delete")
        assert found is not None
        assert found.decision == "block"
        assert found.priority == 10

    def test_create_uses_defaults(self, db_session):
        repo = PolicyRepository(db_session)
        data = dict(VALID_POLICY)
        data.pop("conditions")
        data.pop("combinator")
        data.pop("priority")
        model = repo.create_policy(data)
        db_session.commit()
        assert model.conditions == []
        assert model.combinator == "AND"
        assert model.priority == 0
        assert model.enabled is True

    def test_update_policy_bumps_version(self, db_session):
        repo = PolicyRepository(db_session)
        repo.create_policy(VALID_POLICY)
        db_session.commit()

        updated = repo.update_policy("block_large_delete", {"decision": "require_hitl", "message": "New msg"})
        db_session.commit()
        assert updated.decision == "require_hitl"
        assert updated.message == "New msg"
        assert updated.version == 2

    def test_update_missing_returns_none(self, db_session):
        repo = PolicyRepository(db_session)
        assert repo.update_policy("nope", {"decision": "allow"}) is None

    def test_delete_by_rule_id(self, db_session):
        repo = PolicyRepository(db_session)
        repo.create_policy(VALID_POLICY)
        db_session.commit()
        assert repo.delete_by_rule_id("block_large_delete") is True
        assert repo.find_by_rule_id("block_large_delete") is None
        assert repo.delete_by_rule_id("block_large_delete") is False

    def test_list_all_filters(self, db_session):
        repo = PolicyRepository(db_session)
        repo.create_policy(VALID_POLICY)
        repo.create_policy(
            {**VALID_POLICY, "rule_id": "r2", "tool": "email", "action": "send", "decision": "allow", "enabled": False}
        )
        db_session.commit()

        assert len(repo.list_all()) == 2
        assert len(repo.list_all(enabled_only=True)) == 1
        assert len(repo.list_all(tool="database")) == 1
        assert len(repo.list_all(action="send")) == 1
        assert len(repo.list_all(tool="email", action="send")) == 1
        assert len(repo.list_all(tool="file")) == 0

    def test_find_conflicts(self, db_session):
        repo = PolicyRepository(db_session)
        repo.create_policy(VALID_POLICY)  # block
        repo.create_policy(
            {**VALID_POLICY, "rule_id": "allow_query", "tool": "database", "action": "query", "decision": "allow"}
        )
        db_session.commit()

        conflicts = repo.find_conflicts(tool="database", action="query", decision="block")
        assert [c.rule_id for c in conflicts] == ["allow_query"]

        assert repo.find_conflicts(tool="database", action="delete", decision="block") == []
        assert repo.find_conflicts(tool="database", action="query", decision="block", exclude_rule_id="allow_query") == []

    def test_upsert_from_rule_create_and_update(self, db_session):
        repo = PolicyRepository(db_session)
        repo.upsert_from_rule({"id": "r1", "tool": "db", "action": "x", "decision": "block", "message": "m"})
        db_session.commit()
        assert repo.find_by_rule_id("r1") is not None

        repo.upsert_from_rule({"id": "r1", "tool": "db", "action": "y", "decision": "allow", "message": "m2"})
        db_session.commit()
        model = repo.find_by_rule_id("r1")
        assert model.action == "y"
        assert model.decision == "allow"
        assert model.version == 2

    def test_sync_from_yaml(self, db_session):
        repo = PolicyRepository(db_session)
        rules = [
            {"id": "r1", "tool": "db", "action": "a", "decision": "block", "message": "m"},
            {"id": "r2", "tool": "db", "action": "b", "decision": "allow", "message": "m"},
        ]
        repo.sync_from_yaml(rules)
        assert repo.count() == 2

    def test_find_by_tool_action(self, db_session):
        repo = PolicyRepository(db_session)
        repo.create_policy(VALID_POLICY)
        repo.create_policy({**VALID_POLICY, "rule_id": "r2", "action": "update"})
        db_session.commit()
        assert len(repo.find_by_tool_action("database", "delete")) == 1

    def test_get_all_rules_and_count_by_tool_action(self, db_session):
        repo = PolicyRepository(db_session)
        repo.create_policy(VALID_POLICY)
        db_session.commit()

        rules = repo.get_all_rules()
        assert rules[0]["id"] == "block_large_delete"
        assert set(rules[0]) >= {"id", "tool", "action", "decision"}

        assert repo.count_by_tool_action("database", "delete") == 1
        assert repo.count_by_tool_action("database", "query") == 0
