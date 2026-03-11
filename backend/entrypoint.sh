#!/usr/bin/env bash
set -euo pipefail

# Run migrations (safe to re-run)
alembic upgrade head

# Seed test data (idempotent)
python -m app.seed

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
