#!/usr/bin/env bash
# Run infra without docker-compose — plain `docker run` on a shared network.
# Mirrors docker-compose.yml (postgres :5433, powersync-postgres :5434, powersync :2000).
#
# Usage:
#   scripts/dev.sh up        # start DBs + PowerSync, run migrations
#   scripts/dev.sh down      # stop + remove containers (keeps data volume)
#   scripts/dev.sh nuke      # down + delete data volume
#   scripts/dev.sh migrate   # run goose migrations only
#   scripts/dev.sh status    # container + health status
#   scripts/dev.sh logs <svc># tail logs (postgres|powersync-postgres|powersync)
#   scripts/dev.sh api       # build + run Django in a container (optional)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

NET="inventory-net"
VOL="inventory_pgdata"
PG_IMAGE="postgres:16-alpine"
PS_IMAGE="journeyapps/powersync-service:1.19.0"

PG_NAME="postgres"
PSPG_NAME="powersync-postgres"
PS_NAME="powersync"
API_NAME="inventory-api"

DBSTRING="postgres://postgres:postgres@localhost:5433/db_inventory?sslmode=disable"

log() { printf '\033[1;34m[dev]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[dev]\033[0m %s\n' "$*" >&2; }

require_docker() {
  command -v docker >/dev/null 2>&1 || { err "docker not found"; exit 1; }
  docker info >/dev/null 2>&1 || { err "docker daemon not running"; exit 1; }
}

ensure_net() {
  docker network inspect "$NET" >/dev/null 2>&1 || docker network create "$NET" >/dev/null
}

wait_pg() {
  local name="$1" db="$2"
  log "waiting for $name ..."
  for _ in $(seq 1 30); do
    if docker exec "$name" pg_isready -U postgres -d "$db" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  err "$name not ready"; exit 1
}

start_pg() {
  docker rm -f "$PG_NAME" >/dev/null 2>&1 || true
  log "starting $PG_NAME (:5433, wal_level=logical)"
  docker run -d --name "$PG_NAME" --network "$NET" \
    -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=db_inventory \
    -p 5433:5432 \
    -v "$VOL":/var/lib/postgresql/data \
    "$PG_IMAGE" \
    postgres -c wal_level=logical -c max_wal_senders=10 -c max_replication_slots=10 >/dev/null
  wait_pg "$PG_NAME" db_inventory
}

start_pspg() {
  docker rm -f "$PSPG_NAME" >/dev/null 2>&1 || true
  log "starting $PSPG_NAME (:5434)"
  docker run -d --name "$PSPG_NAME" --network "$NET" \
    -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=db_powersync \
    -p 5434:5432 \
    "$PG_IMAGE" >/dev/null
  wait_pg "$PSPG_NAME" db_powersync
}

start_ps() {
  docker rm -f "$PS_NAME" >/dev/null 2>&1 || true
  log "starting $PS_NAME (:2000)"
  docker run -d --name "$PS_NAME" --network "$NET" \
    -e POWERSYNC_CONFIG_PATH=/app/config/config.yaml \
    -p 2000:2000 \
    -v "$ROOT/powersync/config.yaml":/app/config/config.yaml:ro \
    "$PS_IMAGE" start -r unified >/dev/null
  log "powersync up — http://localhost:2000/probes/liveness"
}

migrate() {
  command -v goose >/dev/null 2>&1 || { err "goose not found. brew install goose"; exit 1; }
  log "running migrations"
  GOOSE_DRIVER=postgres GOOSE_DBSTRING="$DBSTRING" \
    goose -dir "$ROOT/migrations" -table inventory_schema_migrations up
}

start_api() {
  ensure_net
    log "building api image"
    docker build -t inventory-api:dev -f "$ROOT/backend/Dockerfile" "$ROOT" >/dev/null
  docker rm -f "$API_NAME" >/dev/null 2>&1 || true
  log "starting $API_NAME (:8000)"
  docker run -d --name "$API_NAME" --network "$NET" \
    -e DJANGO_SECRET_KEY=dev-docker-secret -e DJANGO_DEBUG=true \
    -e INVENTORY_DB_HOST="$PG_NAME" -e INVENTORY_DB_PORT=5432 \
    -e INVENTORY_DB_NAME=db_inventory -e INVENTORY_DB_USER=postgres -e INVENTORY_DB_PASSWORD=postgres \
    -e POWERSYNC_URL=http://localhost:2000 \
    -e POWERSYNC_JWT_SECRET=inventory-dev-powersync-secret-key-32b \
    -e POWERSYNC_JWT_AUDIENCE=http://localhost:2000 \
    -e CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173 \
    -e GOOGLE_API_KEY="${GOOGLE_API_KEY:-}" \
    -e OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
    -e DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-}" \
    -e OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-}" \
    -e INVENTORY_AGENT_MODEL="${INVENTORY_AGENT_MODEL:-}" \
    -p 8000:8000 \
    inventory-api:dev \
    python manage.py runserver 0.0.0.0:8000 >/dev/null
  log "api up — http://localhost:8000/api/docs/"
}

case "${1:-up}" in
  up)
    require_docker; ensure_net
    start_pg; start_pspg; migrate; start_ps
    cat <<EOF

infra ready (no compose):
  app db        localhost:5433  (db_inventory)
  powersync db  localhost:5434  (db_powersync)
  powersync     http://localhost:2000

next — backend (native):
  cd backend && source .venv/bin/activate
  export DJANGO_SECRET_KEY=dev-secret GOOGLE_API_KEY=...  # or OPENAI_API_KEY
  export INVENTORY_DB_PORT=5433
  python manage.py runserver 8000

next — frontend:
  cd frontend && npm run dev    # VITE_ENABLE_POWERSYNC=true works now

or run api in docker too:  scripts/dev.sh api
EOF
    ;;
  down)
    docker rm -f "$API_NAME" "$PS_NAME" "$PSPG_NAME" "$PG_NAME" >/dev/null 2>&1 || true
    log "containers removed (volume $VOL kept)"
    ;;
  nuke)
    docker rm -f "$API_NAME" "$PS_NAME" "$PSPG_NAME" "$PG_NAME" >/dev/null 2>&1 || true
    docker volume rm "$VOL" >/dev/null 2>&1 || true
    log "containers + volume removed"
    ;;
  migrate) migrate ;;
  api) require_docker; start_api ;;
  status)
    docker ps --filter "network=$NET" --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
    ;;
  logs)
    svc="${2:?usage: dev.sh logs <postgres|powersync-postgres|powersync|inventory-api>}"
    docker logs -f "$svc"
    ;;
  *)
    err "unknown command: $1"
    err "use: up | down | nuke | migrate | api | status | logs <svc>"
    exit 1
    ;;
esac
