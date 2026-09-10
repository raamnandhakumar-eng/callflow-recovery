#!/bin/sh
set -eu

# Keep the public demo available even if an optional external database is
# unavailable (for example, an expired free Render Postgres instance).
# Production deployments should provide a durable DATABASE_URL.
if ! python scripts/seed.py; then
  echo "Primary database unavailable; falling back to ephemeral SQLite demo storage."
  export DATABASE_URL="sqlite:////tmp/callflow.db"
  python scripts/seed.py
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
