"""Repository tests for AuditLogRepository (chained checksums, search, timeline, integrity)."""

import pytest

from app.database.repositories.audit_log_repository import (
    AuditLogRepository,
    audit_content,
    compute_checksum,
)


@pytest.mark.repo
class TestChecksumHelpers:
    def test_compute_checksum_chains_previous(self):
        a = compute_checksum({"a": 1}, None)
        b = compute_checksum({"a": 1}, None)
        c = compute_checksum({"a": 2}, a)
        assert a == b
        assert c != a

    def test_compute_checksum_deterministic(self):
        assert compute_checksum({"b": 1, "a": 2}, "prev") == compute_checksum({"a": 2, "b": 1}, "prev")

    def test_audit_content_includes_core_fields(self):
        from app.database.models.audit_log import AuditLogModel

        m = AuditLogModel(
            tool="database", action="delete", request_data={"tool": "database"}
        )
        content = audit_content(m)
        assert content["tool"] == "database"
        assert content["request_data"] == {"tool": "database"}
        assert "checksum" not in content


@pytest.mark.repo
class TestAuditLogRepository:
    def test_create_chains_checksums(self, db_session):
        repo = AuditLogRepository(db_session)
        r1 = repo.create({"tool": "database"}, {"decision": "allow"}, correlation_id="c1")
        r2 = repo.create({"tool": "database"}, {"decision": "block"}, correlation_id="c2")
        db_session.commit()

        assert r1.prev_checksum is None
        assert r1.checksum
        assert r2.prev_checksum == r1.checksum
        assert r2.checksum != r1.checksum

    def test_find_by_correlation_id(self, db_session):
        repo = AuditLogRepository(db_session)
        repo.create({"tool": "a"}, {"decision": "allow"}, correlation_id="corr_x")
        repo.create({"tool": "b"}, {"decision": "allow"}, correlation_id="corr_y")
        repo.create({"tool": "c"}, {"decision": "allow"}, correlation_id="corr_x")
        db_session.commit()

        items = repo.find_by_correlation_id("corr_x")
        assert len(items) == 2
        assert [i.tool for i in items] == ["a", "c"]

    def test_list_recent_orders_desc(self, db_session):
        repo = AuditLogRepository(db_session)
        repo.create({"tool": "a"}, {"decision": "allow"})
        r2 = repo.create({"tool": "b"}, {"decision": "block"})
        db_session.commit()
        assert repo.list_recent()[0].id == r2.id

    def test_search_filters(self, db_session):
        repo = AuditLogRepository(db_session)
        repo.create({"tool": "database", "action": "delete"}, {"decision": "block", "matched_rule": "r_big"}, correlation_id="corr_abc", actor="admin")
        repo.create({"tool": "email", "action": "send"}, {"decision": "allow"}, correlation_id="corr_xyz")
        db_session.commit()

        filters = {"tool": "database"}
        assert len(repo.search(filters)) == 1

        assert repo.count({"action": "send"}) == 1
        assert repo.count({"decision": "block"}) == 1
        assert repo.count({"search": "corr_abc"}) == 1
        assert repo.count({"actor": "admin"}) == 1
        assert repo.count({"actor": "nobody"}) == 0

        by_match = repo.search({"search": "r_big"})
        assert len(by_match) == 1
        assert by_match[0].correlation_id == "corr_abc"

    def test_search_pagination_and_order(self, db_session):
        repo = AuditLogRepository(db_session)
        for i in range(5):
            repo.create({"tool": "database"}, {"decision": "allow"}, correlation_id=f"c{i}")
        db_session.commit()

        asc = repo.search({}, sort_desc=False)
        assert [r.correlation_id for r in asc] == ["c0", "c1", "c2", "c3", "c4"]
        desc = repo.search({}, sort_desc=True)
        assert desc[0].correlation_id == "c4"
        assert len(repo.search({}, skip=1, limit=2)) == 2

    def test_timeline_sqlite(self, db_session):
        repo = AuditLogRepository(db_session)
        repo.create({"tool": "database"}, {"decision": "block"})
        repo.create({"tool": "email"}, {"decision": "allow"})
        db_session.commit()

        rows = repo.timeline(granularity="hour")
        assert rows
        assert rows[0]["total"] == 2
        assert rows[0]["decisions"]["block"] == 1

        day_rows = repo.timeline(granularity="day")
        assert day_rows[0]["total"] == 2

    def test_verify_integrity_valid(self, db_session):
        repo = AuditLogRepository(db_session)
        for i in range(3):
            repo.create({"tool": "database", "n": i}, {"decision": "allow"}, correlation_id=f"c{i}")
        db_session.commit()

        result = repo.verify_integrity()
        assert result["valid"] is True
        assert result["checked"] == 3
        assert result["errors"] == []

    def test_verify_integrity_detects_tampering(self, db_session):
        repo = AuditLogRepository(db_session)
        repo.create({"tool": "database"}, {"decision": "allow"}, correlation_id="c1")
        r2 = repo.create({"tool": "database"}, {"decision": "block"}, correlation_id="c2")
        db_session.commit()

        r2.decision = "allow"
        db_session.commit()

        result = repo.verify_integrity()
        assert result["valid"] is False
        assert len(result["errors"]) >= 1

    def test_verify_integrity_detects_broken_chain(self, db_session):
        from app.database.repositories.audit_log_repository import audit_content

        repo = AuditLogRepository(db_session)
        r1 = repo.create({"tool": "database"}, {"decision": "allow"})
        repo.create({"tool": "database"}, {"decision": "block"})
        db_session.commit()

        # Re-hash record 1 for the tampered content; record 2 still points at the
        # original checksum, so the chain itself is broken.
        r1.decision = "block"
        r1.checksum = compute_checksum(audit_content(r1), None)
        db_session.commit()

        result = repo.verify_integrity()
        assert result["valid"] is False
        assert any("chain broken" in e for e in result["errors"])
