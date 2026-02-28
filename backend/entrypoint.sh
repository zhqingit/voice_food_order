#!/usr/bin/env bash
set -euo pipefail

# Run migrations (safe to re-run)
alembic upgrade head

# Seed test data (idempotent)
python -m app.seed

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
