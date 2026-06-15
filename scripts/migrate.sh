#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export GOOSE_DRIVER="${GOOSE_DRIVER:-postgres}"
export GOOSE_DBSTRING="${GOOSE_DBSTRING:-postgres://postgres:postgres@localhost:5433/db_inventory?sslmode=disable}"
export GOOSE_MIGRATION_DIR="${GOOSE_MIGRATION_DIR:-$ROOT/migrations}"
export GOOSE_TABLE="${GOOSE_TABLE:-inventory_schema_migrations}"

if ! command -v goose >/dev/null 2>&1; then
  echo "goose not found. Install: mise install (pressly/goose) or brew install goose"
  exit 1
fi

CMD="${1:-up}"
shift || true
goose -dir "$GOOSE_MIGRATION_DIR" "$CMD" "$@"
