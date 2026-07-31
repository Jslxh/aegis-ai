import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db_optional
from app.main import app
from app.observability.metrics import (
    REGISTRY,
    executions_total,
    http_requests_total,
    failures_total,
    security_events_total,
)


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

    import app.api.routes as api_routes_mod
    from app.audit.logger import PostgresAuditLogger
    api_routes_mod.audit = PostgresAuditLogger(TestingSession)

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health_liveness(client):
    res = client.get("/health/live")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["service"] == "guardrail-ai"


def test_health_readiness(client):
    res = client.get("/health/ready")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    components = {c["component"]: c["status"] for c in body["checks"]}
    assert components["database"] == "ok"
    assert components["policy_engine"] == "ok"


def test_metrics_endpoint(client):
    res = client.get("/metrics")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/plain")
    text = res.text
    assert "guardrail_http_requests_total" in text
    assert "guardrail_http_request_duration_seconds" in text
    assert "guardrail_executions_total" in text
    assert "guardrail_failures_total" in text
    assert "guardrail_security_events_total" in text


def test_execute_records_metrics(client):
    before = executions_total._metrics.get(("database", "delete", "allow", "executed"))
    before_val = before._value.get() if before else None
    res = client.post(
        "/execute",
        json={"tool": "database", "action": "delete", "record_count": 5},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["correlation_id"]
    after = executions_total._metrics[("database", "delete", "allow", "executed")]
    after_val = after._value.get()
    assert (after_val if before_val is None else after_val - before_val) >= 1

    text = client.get("/metrics").text
    assert 'guardrail_executions_total{action="delete",decision="allow",status="executed",tool="database"}' in text


def test_block_records_security_event(client):
    res = client.post(
        "/execute",
        json={"tool": "database", "action": "delete", "record_count": 500},
    )
    assert res.status_code == 200
    assert res.json()["decision"] == "block"
    key = ("security.policy_blocked", "high", "blocked")
    assert key in security_events_total._metrics
    assert security_events_total._metrics[key]._value.get() >= 1


def test_http_metrics_record_404(client):
    res = client.get("/does-not-exist")
    assert res.status_code == 404
    key = ("GET", "/does-not-exist", "404")
    assert key in http_requests_total._metrics


def test_correlation_header_accepted(client):
    res = client.post(
        "/execute",
        json={"tool": "database", "action": "delete", "record_count": 5},
        headers={"X-Correlation-ID": "corr_test_abc123"},
    )
    assert res.status_code == 200


def test_metrics_registry_populated(client):
    client.get("/metrics")
    text = client.get("/metrics").text
    assert "# HELP guardrail_http_requests_total" in text
    assert "# TYPE guardrail_http_request_duration_seconds histogram" in text


def test_health_readiness_reports_failure_metric(monkeypatch):
    failures_total._metrics.clear()
    from app.observability import health as health_mod

    health_mod._check_policy_engine(None)
    assert failures_total._metrics.get(("health", "policy_engine_unavailable"))
    assert REGISTRY.get_sample_value(
        "guardrail_failures_total",
        labels={"component": "health", "type": "policy_engine_unavailable"},
    ) >= 1
