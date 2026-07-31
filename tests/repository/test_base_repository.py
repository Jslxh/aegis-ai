"""Repository tests for the generic BaseRepository CRUD helpers."""

import pytest

from app.database.models.execution_history import ExecutionHistoryModel
from app.database.repositories.base import BaseRepository


@pytest.mark.repo
class TestBaseRepository:
    def _make(self, db_session, suffix="0"):
        repo = BaseRepository(db_session, ExecutionHistoryModel)
        model = ExecutionHistoryModel(
            tool="database",
            action="delete",
            request_data={"n": 1},
            decision="allow",
            execution_status="executed",
            correlation_id=f"corr_{suffix}",
        )
        return repo, repo.add(model)

    def test_add_and_get(self, db_session):
        repo, model = self._make(db_session)
        fetched = repo.get(model.id)
        assert fetched is not None
        assert fetched.correlation_id == "corr_0"

    def test_get_missing_returns_none(self, db_session):
        repo = BaseRepository(db_session, ExecutionHistoryModel)
        assert repo.get(9999) is None

    def test_list_orders_desc(self, db_session):
        repo, _ = self._make(db_session, "1")
        _, model2 = self._make(db_session, "2")
        models = repo.list()
        assert models[0].id == model2.id

    def test_list_respects_skip_and_limit(self, db_session):
        repo, _ = self._make(db_session, "1")
        for i in range(2, 5):
            self._make(db_session, str(i))
        assert len(repo.list(skip=0, limit=2)) == 2
        assert len(repo.list(skip=1, limit=10)) == 3

    def test_delete_returns_true_and_removes(self, db_session):
        repo, model = self._make(db_session)
        assert repo.delete(model.id) is True
        assert repo.get(model.id) is None

    def test_delete_missing_returns_false(self, db_session):
        repo = BaseRepository(db_session, ExecutionHistoryModel)
        assert repo.delete(9999) is False

    def test_count(self, db_session):
        repo, _ = self._make(db_session, "1")
        self._make(db_session, "2")
        self._make(db_session, "3")
        assert repo.count() == 3
