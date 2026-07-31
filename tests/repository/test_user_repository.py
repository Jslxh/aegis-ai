"""Repository tests for UserRepository and RefreshTokenRepository."""

from datetime import datetime, timedelta

import pytest

from app.database.repositories.user_repository import UserRepository
from app.database.repositories.refresh_token_repository import RefreshTokenRepository


@pytest.mark.repo
class TestUserRepository:
    def test_create_user_hashes_password(self, db_session):
        repo = UserRepository(db_session)
        user = repo.create_user("alice", "alice@example.com", "SuperSecret123!", role="admin")
        db_session.commit()
        assert user.username == "alice"
        assert user.role == "admin"
        assert user.hashed_password != "SuperSecret123!"
        assert user.is_active is True

    def test_find_by_username_and_email(self, db_session):
        repo = UserRepository(db_session)
        repo.create_user("bob", "bob@example.com", "pass1234")
        db_session.commit()

        assert repo.find_by_username("bob").email == "bob@example.com"
        assert repo.find_by_username("missing") is None
        assert repo.find_by_email("bob@example.com").username == "bob"
        assert repo.find_by_email("missing@example.com") is None

    def test_create_user_default_role(self, db_session):
        repo = UserRepository(db_session)
        user = repo.create_user("carol", "carol@example.com", "pass1234")
        db_session.commit()
        assert user.role == "viewer"


@pytest.mark.repo
class TestRefreshTokenRepository:
    def _seed_user(self, db_session):
        repo = UserRepository(db_session)
        return repo.create_user("dave", "dave@example.com", "pass1234")

    def test_create_and_find_by_hash(self, db_session):
        user = self._seed_user(db_session)
        repo = RefreshTokenRepository(db_session)
        expires = datetime.utcnow() + timedelta(hours=1)
        token = repo.create_token("hash123", user.id, expires)
        db_session.commit()

        assert token.revoked is False
        found = repo.find_by_hash("hash123")
        assert found is not None
        assert found.user_id == user.id
        assert repo.find_by_hash("nope") is None

    def test_revoke_token(self, db_session):
        user = self._seed_user(db_session)
        repo = RefreshTokenRepository(db_session)
        repo.create_token("hash1", user.id, datetime.utcnow() + timedelta(hours=1))
        db_session.commit()

        revoked = repo.revoke_token("hash1")
        assert revoked.revoked is True
        assert repo.revoke_token("missing") is None

    def test_revoke_all_for_user(self, db_session):
        user = self._seed_user(db_session)
        repo = RefreshTokenRepository(db_session)
        expires = datetime.utcnow() + timedelta(hours=1)
        repo.create_token("h1", user.id, expires)
        repo.create_token("h2", user.id, expires)
        db_session.commit()

        repo.revoke_all_for_user(user.id)
        db_session.commit()
        assert repo.find_by_hash("h1").revoked is True
        assert repo.find_by_hash("h2").revoked is True
