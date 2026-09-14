#!/bin/sh
set -eu

# Recruiter demo mode may fall back to ephemeral SQLite so the public demo
# remains usable if an optional external database is unavailable. Strict live
# mode must fail closed instead of silently changing persistence backends.
if ! python scripts/seed.py; then
  if [ "${DEMO_MODE:-false}" = "true" ]; then
    echo "Demo database unavailable; falling back to ephemeral SQLite demo storage."
    export DATABASE_URL="sqlite:////tmp/callflow.db"
    python scripts/seed.py
  else
    echo "Database initialization failed in strict live mode. Refusing to start."
    exit 1
  fi
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
