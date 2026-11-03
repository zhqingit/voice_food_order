#!/usr/bin/env bash
set -euo pipefail

# Run migrations (safe to re-run)
alembic upgrade head

# Demo store with a well-known password: local dev only (idempotent).
if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  python -m app.seed
fi

# WEB_RELOAD=true  → single-worker uvicorn with --reload (dev)
# WEB_RELOAD=false → gunicorn with N uvicorn workers (production)
if [ "${WEB_RELOAD:-false}" = "true" ]; then
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
  exec gunicorn app.main:app \
    --bind 0.0.0.0:8000 \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers "${WEB_WORKERS:-4}" \
    --timeout 120 \
    --graceful-timeout 30 \
    --keep-alive 5
fi
