# Inventory Django API

DRF server on Goose-managed Postgres. Schema lives in `../migrations/` — **do not** `migrate` new tables via Django.

## Setup

```bash
cd inventory
docker compose up -d
./scripts/migrate.sh up

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DJANGO_SECRET_KEY=dev-secret
python manage.py check
python manage.py runserver 8000
```

Demo user (from seed migration): `demo@inventory.local` / `password123`

## Auth

```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@inventory.local","password":"password123"}'
```

Use `Authorization: Bearer <access>` on protected routes.

## Endpoints (JWT unless noted)

| Method | Path | Action |
|--------|------|--------|
| GET/POST | `/api/products/` | list / register |
| GET/PUT/PATCH/DELETE | `/api/products/{id}/` | detail / update / delete |
| GET/POST | `/api/stock/` | on-hand per product / manual add |
| POST | `/api/stock/add/` | manual stock add (alias) |
| GET/POST | `/api/stock-movements/` | list / create manual movement |
| GET/PUT/PATCH/DELETE | `/api/stock-movements/{id}/` | detail / update / delete (manual only) |
| GET/POST | `/api/purchase-orders/` | list / create |
| GET/PUT/PATCH/DELETE | `/api/purchase-orders/{id}/` | detail / update / delete |
| GET/POST | `/api/sales-orders/` | list / create |
| GET/PUT/PATCH/DELETE | `/api/sales-orders/{id}/` | detail / update / delete |
| GET | `/api/financials/` | profit all products |
| GET | `/api/financials/{sku_or_id}/` | profit one product |
| POST | `/api/chat/` | conversational agent (REST) |
| POST | `/api/sync/token/` | mint PowerSync JWT |
| POST | `/api/sync/mutations/` | PowerSync upload connector |
| GET | `/api/sync/jwks/` | HS256 JWKS (local dev) |
| GET | `/api/docs/` | Swagger UI |
| GET | `/api/schema/` | OpenAPI schema |

## PowerSync env

| Var | Default |
|-----|---------|
| `POWERSYNC_URL` | `http://localhost:2000` |
| `POWERSYNC_JWT_SECRET` | `inventory-dev-powersync-secret-key-32b` |
| `POWERSYNC_JWT_AUDIENCE` | `http://localhost:2000` |

Must match `inventory/powersync/config.yaml` `client_auth.jwks`.

## Database env

| Var | Default |
|-----|---------|
| `INVENTORY_DB_HOST` | `localhost` |
| `INVENTORY_DB_PORT` | `5433` |
| `INVENTORY_DB_NAME` | `db_inventory` |
| `GOOGLE_API_KEY` | Gemini API key for `/api/chat/` (default provider) |
| `OPENAI_API_KEY` | optional — use with `INVENTORY_AGENT_MODEL=openai:gpt-4o-mini` |
| `INVENTORY_AGENT_MODEL` | pydantic-ai model id (default: `google-gla:gemini-2.5-flash-lite` when `GOOGLE_API_KEY` is set) |

## Service layout

Business logic is split (one SQL file per query):

| Module | Role |
|--------|------|
| `services/sql/` | Named SQL constants from `../sql/queries/*.sql` (one file per query) |
| `services/ledger.py` | Append-only stock movements + compensating entries |
| `services/products.py` | Product CRUD |
| `services/stock.py` | Stock queries + manual movements |
| `services/orders.py` | Purchase/sales orders (compensating ledger on edit/delete) |
| `services/financials.py` | Profit read model |
| `services/inventory.py` | Facade re-export for REST + AI tools |

Order edits **never delete or mutate** ledger rows — they append compensating `stock_movement` lines.

## Tests

```bash
pytest                    # services + API (skips if Postgres down)
pytest tests/test_api.py  # REST CRUD + auth isolation + example scenario
```
