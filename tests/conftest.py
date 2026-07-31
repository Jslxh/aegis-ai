"""Shared pytest fixtures for the Guardrail AI test suite.

The suite runs against an in-memory SQLite database (StaticPool) with the
application's dependency injection overridden so every API test is hermetic
and never touches PostgreSQL or the filesystem audit log.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db, get_db_optional
from app.main import app
from app.auth.security import create_access_token, hash_password

TEST_PASSWORD = "TestPassw0rd!"
# bcrypt is deliberately slow; compute the hash once and reuse for every seeded
# user so the shared `client` fixture stays fast.
_TEST_USER_HASH = hash_password(TEST_PASSWORD)


@pytest.fixture(scope="session")
def sqlite_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture()
def session_factory(sqlite_engine):
    return sessionmaker(bind=sqlite_engine)


@pytest.fixture()
def db_session(session_factory):
    session = session_factory()
    try:
        _wipe_tables(session)
        yield session
    finally:
        _wipe_tables(session)
        session.close()


def _wipe_tables(session):
    """Delete all rows so each test starts from a clean in-memory DB."""
    from app.database.session import Base

    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()


def _override_dependencies(session_factory):
    """Point both DB dependencies at the in-memory session factory."""
    def override_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    def override_db_optional():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_db_optional] = override_db_optional
    app.state.session_factory = session_factory


def _wire_audit_logger(session_factory):
    """Route audit writes (and simulation persistence) to the in-memory DB."""
    import app.api.routes as routes
    from app.audit.logger import PostgresAuditLogger
    from app.simulator.simulation import Simulation

    routes.audit = PostgresAuditLogger(session_factory)
    routes.simulation = Simulation(session_factory=session_factory)


@pytest.fixture()
def client(session_factory):
    """TestClient wired to the in-memory SQLite database."""
    _override_dependencies(session_factory)
    _wire_audit_logger(session_factory)

    client = TestClient(app)

    session = session_factory()
    try:
        _wipe_tables(session)
        seed_user(session, username="admin", role="admin")
        seed_user(session, username="security_analyst", role="security_analyst")
        seed_user(session, username="auditor", role="auditor")
        seed_user(session, username="operator", role="operator")
        seed_user(session, username="viewer", role="viewer")
        session.commit()
    finally:
        session.close()

    yield client

    session = session_factory()
    try:
        _wipe_tables(session)
    finally:
        session.close()
    app.dependency_overrides.clear()


@pytest.fixture()
def unauth_client(session_factory):
    """TestClient that does not seed users (for 401/503 path tests)."""
    _override_dependencies(session_factory)
    _wire_audit_logger(session_factory)
    session = session_factory()
    try:
        _wipe_tables(session)
    finally:
        session.close()
    client = TestClient(app)
    yield client
    session = session_factory()
    try:
        _wipe_tables(session)
    finally:
        session.close()
    app.dependency_overrides.clear()


def seed_user(session, username: str, role: str = "viewer", email: str | None = None):
    """Insert a user row directly (fast, avoids re-hashing per test)."""
    from app.database.models.user import UserModel

    if not email:
        email = f"{username}@example.com"
    user = UserModel(
        username=username,
        email=email,
        hashed_password=_TEST_USER_HASH,
        role=role,
        is_active=True,
    )
    session.add(user)
    return user


def auth_header(session, username: str = "admin", role: str | None = None) -> dict:
    """Build an Authorization header for a given user."""
    from app.database.repositories.user_repository import UserRepository

    repo = UserRepository(session)
    user = repo.find_by_username(username)
    if user is None:
        user = seed_user(session, username=username, role=role or "viewer")
        session.commit()
    token = create_access_token(
        {"sub": str(user.id), "username": user.username, "role": user.role}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def auth_headers_factory(session_factory):
    """Factory producing Authorization headers for arbitrary roles."""
    def _make(role: str = "admin") -> dict:
        session = session_factory()
        try:
            from app.database.repositories.user_repository import UserRepository

            repo = UserRepository(session)
            user = repo.find_by_username(role)
            if user is None:
                user = seed_user(session, username=role, role=role)
                session.commit()
            return {
                "Authorization": "Bearer "
                + create_access_token(
                    {"sub": str(user.id), "username": user.username, "role": user.role}
                )
            }
        finally:
            session.close()

    return _make


@pytest.fixture()
def mock_groq(monkeypatch):
    """Replace GroqService with the real service if GROQ_API_KEY is available,
    otherwise fall back to a deterministic fake."""
    import os
    from dotenv import load_dotenv
    from app.api import ai_routes
    from app.services.groq_service import GroqService

    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        try:
            real_service = GroqService(api_key=api_key)
            ai_routes.groq = real_service
            monkeypatch.setattr(ai_routes, "groq", real_service)
            yield real_service
            return
        except Exception:
            pass

    class FakeGroq:
        def __init__(self, *args, **kwargs):
            pass

        def chat(self, messages, temperature=0.3, max_tokens=1024):
            return {
                "success": True,
                "content": (
                    '{"explanation": "AI explanation", "risk_level": "low", '
                    '"recommendations": ["review"], "confidence": 0.9, "summary": "sum"}'
                ),
                "model": "fake-model",
                "latency": 0.01,
            }

        explain_decision = lambda self, *a, **k: self.chat([])
        analyze_risk = lambda self, *a, **k: self.chat([])
        hitl_summary = lambda self, *a, **k: self.chat([])
        audit_summary = lambda self, *a, **k: self.chat([])
        simulation_analysis = lambda self, *a, **k: self.chat([])

        def run_chat_agent(self, message, history=None):
            return {
                "success": True,
                "is_tool_call": False,
                "response": "Hello from Fake Chat Agent!",
                "tool_call": None
            }

    fake_service = FakeGroq()
    ai_routes.groq = fake_service
    monkeypatch.setattr(ai_routes, "groq", fake_service)
    yield fake_service
    monkeypatch.setattr(ai_routes, "groq", None)
