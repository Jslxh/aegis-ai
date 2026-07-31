"""Unit tests for auth security primitives (password hashing, JWTs, RBAC)."""

from datetime import timedelta

import pytest
from jose import jwt

from app.auth import security


@pytest.mark.unit
class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = security.hash_password("SuperSecret1!")
        assert hashed != "SuperSecret1!"
        assert security.verify_password("SuperSecret1!", hashed) is True

    def test_wrong_password_rejected(self):
        hashed = security.hash_password("SuperSecret1!")
        assert security.verify_password("WrongPass", hashed) is False

    def test_hashes_are_salted(self):
        h1 = security.hash_password("same-pass")
        h2 = security.hash_password("same-pass")
        assert h1 != h2

    def test_verify_malformed_hash_returns_false(self):
        assert security.verify_password("any", "not-a-hash") is False
        assert security.verify_password("any", "") is False


@pytest.mark.unit
class TestTokenHelpers:
    def test_create_and_decode_access_token(self):
        token = security.create_access_token({"sub": "1", "username": "alice", "role": "admin"})
        payload = security.decode_token(token)
        assert payload["sub"] == "1"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_create_and_decode_refresh_token(self):
        token = security.create_refresh_token({"sub": "2"})
        payload = security.decode_token(token)
        assert payload["type"] == "refresh"

    def test_token_type_distinct(self):
        access = security.create_access_token({"sub": "1"})
        refresh = security.create_refresh_token({"sub": "1"})
        assert security.decode_token(access)["type"] == "access"
        assert security.decode_token(refresh)["type"] == "refresh"

    def test_custom_expiry(self):
        token = security.create_access_token({"sub": "1"}, expires_delta=timedelta(minutes=5))
        payload = security.decode_token(token)
        assert payload["type"] == "access"

    def test_decode_invalid_token_returns_none(self):
        assert security.decode_token("garbage.token.value") is None
        assert security.decode_token("") is None

    def test_expired_token_returns_none(self):
        token = security.create_access_token(
            {"sub": "1"}, expires_delta=timedelta(seconds=-60)
        )
        assert security.decode_token(token) is None

    def test_hash_token_is_stable_sha256(self):
        t = "refresh-token-value"
        assert security.hash_token(t) == security.hash_token(t)
        assert len(security.hash_token(t)) == 64
        assert security.hash_token(t) != t


@pytest.mark.unit
class TestRBAC:
    def test_role_levels_ordered(self):
        assert security.role_level("viewer") < security.role_level("operator")
        assert security.role_level("operator") < security.role_level("auditor")
        assert security.role_level("auditor") < security.role_level("security_analyst")
        assert security.role_level("security_analyst") < security.role_level("admin")

    def test_unknown_role_level_zero(self):
        assert security.role_level("nonexistent") == 0

    def test_sufficient_role(self):
        assert security.has_sufficient_role("admin", "viewer") is True
        assert security.has_sufficient_role("admin", "admin") is True
        assert security.has_sufficient_role("viewer", "admin") is False
        assert security.has_sufficient_role("auditor", "operator") is True
