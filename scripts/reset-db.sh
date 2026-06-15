#!/usr/bin/env bash
# Wipe inventory Postgres and re-run Goose migrations (fresh demo seed).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found"
  exit 1
fi

echo "Stopping stack and removing Postgres volume..."
docker compose down -v

echo "Starting Postgres..."
docker compose up -d postgres

echo "Waiting for Postgres..."
for _ in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U postgres -d db_inventory >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "Running migrations..."
"$ROOT/scripts/migrate.sh" up

echo "Starting full stack..."
docker compose up -d

cat <<'EOF'

Fresh database ready.

Login: demo@inventory.local / password123

Seed snapshot:
  A      — Product A (sold out, $900 profit on dashboard)
  CB-01  — Craft Beer IPA 12oz (400 units) — chat PO demo target
  OL-01  — Olive Oil EVOO 750mL (24 units)

Chat history: empty
EOF
