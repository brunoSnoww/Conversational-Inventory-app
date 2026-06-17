#!/usr/bin/env bash
# Wipe inventory Postgres and re-run Goose migrations (fresh demo seed).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DEMO_EMAIL="demo@inventory.local"
DEMO_PASSWORD="KaizntreeDemo1!"

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

echo "Waiting for API..."
for _ in $(seq 1 45); do
  if docker compose exec -T api python manage.py shell -c "print('ok')" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "Setting demo user password..."
docker compose exec -T api python manage.py shell -c "
from accounts.models import AppUser
u = AppUser.objects.get(email='${DEMO_EMAIL}')
u.set_password('${DEMO_PASSWORD}')
u.save(update_fields=['password'])
"

cat <<EOF

Fresh database ready.

Login: ${DEMO_EMAIL} / ${DEMO_PASSWORD}

Seed snapshot:
  A      — Product A (sold out, \$900 profit on dashboard)
  CB-01  — Craft Beer IPA 12oz (400 units) — chat PO demo target
  OL-01  — Olive Oil EVOO 750mL (24 units)

Chat history: empty
EOF
