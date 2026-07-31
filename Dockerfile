# ============================================================================
# Guardrail AI - Production image (multi-stage, non-root)
#
#   docker build -t guardrail-ai:latest .
#   docker run --rm -p 8000:8000 --env-file .env guardrail-ai:latest
# ============================================================================

# ---- Builder stage: install dependencies into a virtualenv -----------------
FROM python:3.10-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Runtime stage ----------------------------------------------------------
FROM python:3.10-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    HOST=0.0.0.0 \
    PORT=8000

# Dedicated unprivileged user (never run the API as root).
RUN groupadd --system guardrail \
    && useradd --system --gid guardrail --home-dir /app guardrail

WORKDIR /app

# Copy the self-contained virtualenv from the builder stage.
COPY --from=builder /opt/venv /opt/venv

# Copy application sources (build context is filtered by .dockerignore).
COPY . .

# Entrypoint (DB readiness + Alembic migrations) and writable logs dir.
RUN mkdir -p /app/logs \
    && chmod +x /app/docker-entrypoint.sh \
    && chown -R guardrail:guardrail /app

USER guardrail

EXPOSE 8000

# Container health check against the liveness endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3)"]

ENTRYPOINT ["/app/docker-entrypoint.sh"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
