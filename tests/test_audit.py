import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db_optional
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)

    def override():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_optional] = override
    app.state.session_factory = TestingSession

    with TestClient(app) as c:
        import app.api.routes as api_routes_mod
        from app.audit.logger import PostgresAuditLogger
        api_routes_mod.audit = PostgresAuditLogger(TestingSession)

        session = TestingSession()
        from app.database.models.user import UserModel
        session.add(
            UserModel(
                username="tester",
                email="tester@example.com",
                hashed_password="unused-hash",
                role="admin",
                is_active=True,
            )
        )
        session.commit()
        session.close()

        yield c
    app.dependency_overrides.clear()


def _auth_headers(client: TestClient, role: str) -> dict:
    from app.auth.security import create_access_token
    token = create_access_token({"sub": "1", "username": "tester", "role": role})
    return {"Authorization": f"Bearer {token}"}


def test_execute_returns_trace_ids(client):
    res = client.post(
        "/execute",
        json={"tool": "database", "action": "delete", "record_count": 5},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["correlation_id"].startswith("corr_")
    assert body["request_id"].startswith("req_")
    assert body["execution_id"].startswith("exec_")


def test_audit_logs_search(client):
    client.post(
        "/execute",
        json={"tool": "database", "action": "delete", "record_count": 5},
    )
    res = client.get(
        "/audit/logs", headers=_auth_headers(client, "auditor")
    )
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    assert body["items"][0]["tool"] == "database"
    assert body["items"][0]["correlation_id"]


def test_audit_requires_auditor(client):
    res = client.get("/audit/logs")
    assert res.status_code == 401


def test_audit_verify_integrity(client):
    client.post(
        "/execute",
        json={"tool": "database", "action": "delete", "record_count": 5},
    )
    res = client.get(
        "/audit/verify", headers=_auth_headers(client, "auditor")
    )
    assert res.status_code == 200
    body = res.json()
    assert body["valid"] is True
    assert body["checked"] >= 1


def test_audit_correlation_chain(client):
    res = client.post(
        "/execute",
        json={"tool": "database", "action": "delete", "record_count": 5},
    )
    correlation_id = res.json()["correlation_id"]

    res = client.get(
        f"/audit/correlation/{correlation_id}",
        headers=_auth_headers(client, "auditor"),
    )
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1
    assert all(i["correlation_id"] == correlation_id for i in items)


def test_audit_export_csv(client):
    client.post(
        "/execute",
        json={"tool": "database", "action": "delete", "record_count": 5},
    )
    res = client.get(
        "/audit/export/csv", headers=_auth_headers(client, "auditor")
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    assert "correlation_id" in res.text


def test_audit_timeline(client):
    client.post(
        "/execute",
        json={"tool": "database", "action": "delete", "record_count": 5},
    )
    res = client.get(
        "/audit/timeline?granularity=hour",
        headers=_auth_headers(client, "auditor"),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["granularity"] == "hour"
    assert isinstance(body["points"], list)


def test_execute_audit_filter_by_decision(client):
    client.post(
        "/execute",
        json={"tool": "database", "action": "delete", "record_count": 5},
    )
    res = client.get(
        "/audit/logs?decision=allow",
        headers=_auth_headers(client, "auditor"),
    )
    assert res.status_code == 200
    assert res.json()["total"] >= 1
