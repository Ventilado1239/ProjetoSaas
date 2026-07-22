#!/bin/sh
set -eu

if [ -n "${MIGRATION_DATABASE_URL:-}" ]; then
  DATABASE_URL="$MIGRATION_DATABASE_URL" alembic upgrade head
  unset MIGRATION_DATABASE_URL
elif [ "${ENVIRONMENT:-development}" = "production" ]; then
  echo "MIGRATION_DATABASE_URL obrigatoria em producao." >&2
  exit 1
else
  alembic upgrade head
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
