"""API tests for authentication: register, login, refresh, logout, me, and RBAC."""

import pytest

from app.auth.security import decode_token, hash_token
from app.database.repositories.refresh_token_repository import RefreshTokenRepository
from app.database.repositories.user_repository import UserRepository

TEST_PASSWORD = "TestPassw0rd!"


def _login(client, username="admin", password=TEST_PASSWORD):
    return client.post("/auth/login", json={"username": username, "password": password})


@pytest.mark.api
class TestRegister:
    def test_register_success(self, client, auth_headers_factory):
        res = client.post(
            "/auth/register",
            json={"username": "newuser", "email": "new@example.com", "password": "Str0ngPass!", "role": "operator"},
            headers=auth_headers_factory("admin"),
        )
        assert res.status_code == 201
        body = res.json()
        assert body["username"] == "newuser"
        assert body["role"] == "operator"

    def test_register_duplicate_username(self, client, auth_headers_factory):
        res = client.post(
            "/auth/register",
            json={"username": "admin", "email": "other@example.com", "password": "Str0ngPass!", "role": "viewer"},
            headers=auth_headers_factory("admin"),
        )
        assert res.status_code == 409

    def test_register_duplicate_email(self, client, auth_headers_factory):
        res = client.post(
            "/auth/register",
            json={"username": "someone", "email": "admin@example.com", "password": "Str0ngPass!", "role": "viewer"},
            headers=auth_headers_factory("admin"),
        )
        assert res.status_code == 409

    def test_register_invalid_role(self, client, auth_headers_factory):
        res = client.post(
            "/auth/register",
            json={"username": "x", "email": "x@example.com", "password": "Str0ngPass!", "role": "superadmin"},
            headers=auth_headers_factory("admin"),
        )
        assert res.status_code == 422

    def test_register_requires_admin(self, client, auth_headers_factory):
        res = client.post(
            "/auth/register",
            json={"username": "x", "email": "x@example.com", "password": "Str0ngPass!", "role": "viewer"},
            headers=auth_headers_factory("security_analyst"),
        )
        assert res.status_code == 403

    def test_register_requires_auth(self, client):
        res = client.post(
            "/auth/register",
            json={"username": "x", "email": "x@example.com", "password": "Str0ngPass!", "role": "viewer"},
        )
        assert res.status_code == 401


@pytest.mark.api
class TestLogin:
    def test_login_success(self, client):
        res = _login(client)
        assert res.status_code == 200
        body = res.json()
        assert body["access_token"]
        assert body["refresh_token"]
        assert decode_token(body["access_token"])["type"] == "access"

    def test_login_wrong_password(self, client):
        res = _login(client, password="wrong")
        assert res.status_code == 401

    def test_login_unknown_user(self, client):
        res = _login(client, username="ghost")
        assert res.status_code == 401

    def test_login_disabled_account(self, client, session_factory):
        session = session_factory()
        try:
            repo = UserRepository(session)
            user = repo.find_by_username("viewer")
            user.is_active = False
            session.commit()
        finally:
            session.close()
        res = _login(client, username="viewer")
        assert res.status_code == 403

    def test_login_stores_refresh_token(self, client, session_factory):
        res = _login(client)
        session = session_factory()
        try:
            token_hash = hash_token(res.json()["refresh_token"])
            assert RefreshTokenRepository(session).find_by_hash(token_hash) is not None
        finally:
            session.close()


@pytest.mark.api
class TestRefresh:
    def test_refresh_rotates_tokens(self, client, session_factory):
        login = _login(client).json()
        old_refresh = login["refresh_token"]

        res = client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert res.status_code == 200
        body = res.json()
        assert body["access_token"]
        assert body["refresh_token"] != old_refresh

        session = session_factory()
        try:
            repo = RefreshTokenRepository(session)
            assert repo.find_by_hash(hash_token(old_refresh)).revoked is True
            assert repo.find_by_hash(hash_token(body["refresh_token"])) is not None
        finally:
            session.close()

    def test_refresh_rejects_access_token(self, client):
        access = _login(client).json()["access_token"]
        res = client.post("/auth/refresh", json={"refresh_token": access})
        assert res.status_code == 401

    def test_refresh_rejects_garbage(self, client):
        res = client.post("/auth/refresh", json={"refresh_token": "not.a.token"})
        assert res.status_code == 401

    def test_refresh_rejects_unknown_hash(self, client):
        from app.auth.security import create_refresh_token

        token = create_refresh_token({"sub": "999", "username": "ghost", "role": "viewer"})
        res = client.post("/auth/refresh", json={"refresh_token": token})
        assert res.status_code == 401

    def test_refresh_rejects_revoked(self, client, session_factory):
        login = _login(client).json()
        refresh = login["refresh_token"]
        session = session_factory()
        try:
            RefreshTokenRepository(session).revoke_token(hash_token(refresh))
            session.commit()
        finally:
            session.close()
        res = client.post("/auth/refresh", json={"refresh_token": refresh})
        assert res.status_code == 401

    def test_refresh_rejects_expired(self, client, session_factory):
        from datetime import datetime, timedelta

        from app.auth.security import create_refresh_token

        login = _login(client).json()
        refresh = login["refresh_token"]
        session = session_factory()
        try:
            stored = RefreshTokenRepository(session).find_by_hash(hash_token(refresh))
            stored.expires_at = datetime.utcnow() - timedelta(days=1)
            session.commit()
        finally:
            session.close()
        res = client.post("/auth/refresh", json={"refresh_token": refresh})
        assert res.status_code == 401


@pytest.mark.api
class TestMe:
    def test_me_returns_current_user(self, client, auth_headers_factory):
        res = client.get("/auth/me", headers=auth_headers_factory("security_analyst"))
        assert res.status_code == 200
        body = res.json()
        assert body["username"] == "security_analyst"
        assert body["role"] == "security_analyst"

    def test_me_requires_auth(self, client):
        assert client.get("/auth/me").status_code == 401

    def test_me_rejects_bad_token(self, client):
        res = client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
        assert res.status_code == 401


@pytest.mark.api
class TestLogout:
    def test_logout_revokes_refresh_token(self, client, session_factory):
        login = _login(client).json()
        refresh = login["refresh_token"]
        res = client.post(
            "/auth/logout",
            json={"refresh_token": refresh},
            headers={"Authorization": f"Bearer {login['access_token']}"},
        )
        assert res.status_code == 200
        session = session_factory()
        try:
            assert RefreshTokenRepository(session).find_by_hash(hash_token(refresh)).revoked is True
        finally:
            session.close()

    def test_logout_requires_auth(self, client):
        res = client.post("/auth/logout", json={"refresh_token": "whatever"})
        assert res.status_code == 401

    def test_logout_foreign_token_still_succeeds(self, client, auth_headers_factory, session_factory):
        login = _login(client, username="operator").json()
        res = client.post(
            "/auth/logout",
            json={"refresh_token": login["refresh_token"]},
            headers=auth_headers_factory("admin"),
        )
        assert res.status_code == 200


@pytest.mark.api
class TestChangePassword:
    def test_change_password_success(self, client, auth_headers_factory):
        res = client.post(
            "/auth/change-password",
            json={"current_password": TEST_PASSWORD, "new_password": "new_secret_pass"},
            headers=auth_headers_factory("viewer"),
        )
        assert res.status_code == 200
        # Verify old login fails
        assert _login(client, username="viewer", password=TEST_PASSWORD).status_code == 401
        # Verify new login succeeds
        assert _login(client, username="viewer", password="new_secret_pass").status_code == 200

    def test_change_password_incorrect_current(self, client, auth_headers_factory):
        res = client.post(
            "/auth/change-password",
            json={"current_password": "incorrect_pass", "new_password": "new_secret_pass"},
            headers=auth_headers_factory("viewer"),
        )
        assert res.status_code == 400


@pytest.mark.api
class TestPasswordReset:
    def test_forgot_password_success(self, client, session_factory):
        res = client.post("/auth/forgot-password", json={"identity": "admin"})
        assert res.status_code == 200
        
        session = session_factory()
        try:
            repo = UserRepository(session)
            user = repo.find_by_username("admin")
            assert user.reset_token is not None
            assert user.reset_token_expires_at is not None
            
            # Now reset using that token
            reset_res = client.post(
                "/auth/reset-password",
                json={"token": user.reset_token, "new_password": "brand_new_pass"}
            )
            assert reset_res.status_code == 200
            
            # Verify new login works
            assert _login(client, username="admin", password="brand_new_pass").status_code == 200
        finally:
            session.close()

    def test_reset_password_invalid_token(self, client):
        res = client.post(
            "/auth/reset-password",
            json={"token": "fake_token", "new_password": "brand_new_pass"}
        )
        assert res.status_code == 400
