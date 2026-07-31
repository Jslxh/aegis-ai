from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database.session import get_db_optional
from app.observability import health
from app.observability.metrics import REGISTRY

router = APIRouter(tags=["observability"])


@router.get("/health/live")
def health_live():
    return health.liveness()


@router.get("/health/ready")
def health_ready(
    request: Request,
    db: Optional[Session] = Depends(get_db_optional),
):
    from app.api.routes import policy_engine

    return health.readiness(
        db=db,
        policy_engine=policy_engine,
        app_state=request.app.state,
    )


@router.get("/metrics")
def metrics():
    if REGISTRY is None:
        return Response(status_code=503, content=b"Prometheus disabled")
    from prometheus_client import generate_latest

    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
