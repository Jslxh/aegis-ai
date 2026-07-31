"""Unit tests for the audit loggers (file JSONL and PostgreSQL-backed)."""

import json
import os

import pytest

from app.audit.logger import FileAuditLogger, PostgresAuditLogger, AuditLogger, BaseAuditLogger


class _ConcreteLogger(BaseAuditLogger):
    def log(self, request, decision, **context):
        return super().log(request, decision, **context)


@pytest.mark.unit
class TestBaseAuditLogger:
    def test_abstract_log_is_noop(self):
        assert _ConcreteLogger().log({}, {}) is None

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseAuditLogger()


@pytest.mark.unit
class TestFileAuditLogger:
    def test_writes_jsonl_records(self, tmp_path):
        path = str(tmp_path / "audit.log")
        logger = FileAuditLogger(path)
        logger.log(
            {"tool": "database", "action": "delete"},
            {"decision": "block", "matched_rule": "r1", "reason": "no"},
            correlation_id="corr_1",
            execution_id="exec_1",
        )

        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["tool"] == "database"
        assert record["decision"] == "block"
        assert record["correlation_id"] == "corr_1"
        assert record["request"]["tool"] == "database"
        assert "timestamp" in record

    def test_appends_multiple_records(self, tmp_path):
        path = str(tmp_path / "audit.log")
        logger = FileAuditLogger(path)
        for i in range(3):
            logger.log({"tool": "database"}, {"decision": "allow"})
        with open(path) as f:
            assert len(f.readlines()) == 3

    def test_creates_parent_directory(self, tmp_path):
        path = str(tmp_path / "nested" / "dirs" / "audit.log")
        logger = FileAuditLogger(path)
        logger.log({"tool": "file"}, {"decision": "allow"})
        assert os.path.exists(path)

    def test_drops_none_context_values(self, tmp_path):
        path = str(tmp_path / "audit.log")
        logger = FileAuditLogger(path)
        logger.log({"tool": "database"}, {"decision": "allow"}, correlation_id=None)
        with open(path) as f:
            record = json.loads(f.readline())
        assert "correlation_id" not in record


@pytest.mark.unit
class TestPostgresAuditLogger:
    def test_writes_to_database(self, session_factory):
        logger = PostgresAuditLogger(session_factory)
        logger.log(
            {"tool": "database", "action": "delete"},
            {"decision": "block", "matched_rule": "r1", "reason": "no"},
            correlation_id="corr_pg",
        )

        session = session_factory()
        try:
            from app.database.models.audit_log import AuditLogModel

            record = session.query(AuditLogModel).first()
            assert record is not None
            assert record.correlation_id == "corr_pg"
            assert record.checksum
        finally:
            session.close()

    def test_rolls_back_on_error(self, session_factory):
        def broken_factory():
            raise RuntimeError("boom")

        logger = PostgresAuditLogger(broken_factory)
        with pytest.raises(RuntimeError):
            logger.log({"tool": "database"}, {"decision": "allow"})

    def test_rolls_back_when_commit_fails(self, session_factory, monkeypatch):
        import sqlalchemy.exc
        from app.database.repositories.audit_log_repository import AuditLogRepository

        class FailingSession:
            def __init__(self):
                self.rolled_back = False

            def commit(self):
                raise sqlalchemy.exc.OperationalError("stmt", {}, Exception("disk full"))

            def rollback(self):
                self.rolled_back = True

            def close(self):
                pass

        monkeypatch.setattr(AuditLogRepository, "create", lambda self, *a, **k: None)

        failing = FailingSession()
        logger = PostgresAuditLogger(lambda: failing)
        with pytest.raises(sqlalchemy.exc.OperationalError):
            logger.log({"tool": "database"}, {"decision": "allow"})
        assert failing.rolled_back is True


@pytest.mark.unit
class TestAuditLoggerAlias:
    def test_alias_is_file_logger(self):
        logger = AuditLogger()
        assert isinstance(logger, FileAuditLogger)
