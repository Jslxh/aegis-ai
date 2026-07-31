#!/bin/sh
# ============================================================================
# Guardrail AI container entrypoint
#
# 1. Waits for PostgreSQL to accept connections (via DATABASE_URL).
# 2. Runs `alembic upgrade head` to bring the schema to the latest revision.
#    If the DB is unreachable or migrations fail on an already-provisioned
#    database (e.g. tables created by the dev bootstrap), falls back to
#    Base.metadata.create_all so the app still boots.
# 3. Executes the container command (uvicorn by default).
#
# Set SKIP_MIGRATIONS=1 to disable step 2 entirely.
# ============================================================================

set -e

# --- 1. Wait for the database ------------------------------------------------
python - <<'PY'
import os
import sys
import time

from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL", "")
if not url:
    sys.exit(0)

engine = create_engine(url, pool_pre_ping=True)
for attempt in range(60):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database is ready.", flush=True)
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        print(f"Waiting for database ({attempt + 1}/60): {exc}", flush=True)
        time.sleep(2)

print("ERROR: database did not become ready in time", flush=True)
sys.exit(1)
PY

# --- 2. Run migrations -------------------------------------------------------
if [ "${SKIP_MIGRATIONS:-0}" = "1" ]; then
    echo "Skipping migrations (SKIP_MIGRATIONS=1)."
elif alembic upgrade head; then
    echo "Database schema is up to date."
else
    echo "WARNING: 'alembic upgrade head' failed; falling back to create_all bootstrap."
    python -c "from app.database.session import Base, engine; from app.database import models; Base.metadata.create_all(bind=engine)"
fi

# --- 3. Launch the application -----------------------------------------------
exec "$@"
