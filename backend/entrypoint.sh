#!/usr/bin/env bash
set -euo pipefail

# Run migrations (safe to re-run)
alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
