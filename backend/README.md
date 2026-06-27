# Inventory FastAPI

FastAPI server on Goose-managed Postgres. Schema lives in `../migrations/` — **do not** manage schema from the app.

## Setup

```bash
cd inventory/Conversational-Inventory-app
docker compose up -d
./scripts/migrate.sh up

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export APP_SECRET_KEY=dev-secret
uvicorn app.main:app --reload --port 8000
```

Demo user: `demo@inventory.local` / `password123` (seed migration and `./scripts/reset-db.sh`)

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
| GET | `/api/stock/` | on-hand per product |
| POST | `/api/stock/add/` | manual stock add |
| GET/POST | `/api/stock-movements/` | list / create manual movement |
| GET/PUT/PATCH/DELETE | `/api/stock-movements/{id}/` | detail / update / delete (manual only) |
| GET/POST | `/api/purchase-orders/` | list / create |
| GET/PUT/PATCH/DELETE | `/api/purchase-orders/{id}/` | detail / update / delete |
| GET/POST | `/api/sales-orders/` | list / create |
| GET/PUT/PATCH/DELETE | `/api/sales-orders/{id}/` | detail / update / delete |
| GET | `/api/financials/{sku_or_id}/` | profit for one product |
| POST | `/api/sync/token/` | mint PowerSync JWT |
| POST | `/api/sync/mutations/` | PowerSync upload connector (chat + agent) |
| GET | `/api/sync/jwks/` | HS256 JWKS (local dev) |
| GET | `/docs` | OpenAPI Swagger UI |

Chat is **not** a REST endpoint — user messages upload via PowerSync; `app/sync/mutations.py` runs the agent and writes the assistant reply.

## PowerSync env

Configured in `app/sync/jwt.py` (must match `../powersync/config.yaml` `client_auth.jwks`):

| Var | Default |
|-----|---------|
| `POWERSYNC_URL` | `http://localhost:2000` |
| `POWERSYNC_JWT_SECRET` | `inventory-dev-powersync-secret-key-32b` |
| `POWERSYNC_JWT_AUDIENCE` | `http://localhost:2000` |

## Database & agent env

| Var | Default |
|-----|---------|
| `APP_SECRET_KEY` | dev-only (JWT signing) |
| `INVENTORY_DB_HOST` | `localhost` |
| `INVENTORY_DB_PORT` | `5433` |
| `INVENTORY_DB_NAME` | `db_inventory` |
| `OPENROUTER_API_KEY` | preferred chat provider (keys start with `sk-or-`) |
| `GOOGLE_API_KEY` | optional — Gemini fallback |
| `DEEPSEEK_API_KEY` | optional — DeepSeek fallback |
| `OPENAI_API_KEY` | optional — OpenAI fallback |
| `INVENTORY_AGENT_MODEL` | override pydantic-ai model id |

Default model resolution (`app/config.py`): explicit `INVENTORY_AGENT_MODEL` → OpenRouter GPT-4o → Gemini → DeepSeek → `openai:gpt-4o`.

## Service layout

| Module | Role |
|--------|------|
| `app/` | FastAPI routers, auth, sync, psycopg pool |
| `domain/models.py` | Rich domain entities with validation rules |
| `domain/exceptions.py` | Domain errors (`UnknownProduct`, `InsufficientStock`, …) |
| `services/repositories/` | SQL persistence — returns domain models |
| `services/services/` | Business orchestration, `@atomic` transactions, DI |
| `services/dtos/` | Typed service response objects |
| `services/inventory.py` | Backward-compatible `*_sync` facade for HTTP and AI tools |
| `services/container.py` | Wires repositories → services |
| `services/db.py` | Postgres helpers (`fetch_one`, `fetch_all`) |
| `ai/` | pydantic-ai agent, guardrails, tools |

Order edits **never delete or mutate** ledger rows — they append compensating `stock_movement` lines.

## Tests

```bash
pytest                    # services + API (skips if Postgres down)
pytest tests/test_api.py  # REST CRUD + auth isolation + example scenario
```
