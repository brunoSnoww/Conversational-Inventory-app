# Inventory

Conversational inventory management for F&B/CPG brands. Chat with an LLM agent
("buy 100 units of CB-01 for $200") and watch a live dashboard update — offline-capable,
no manual refresh, no cache wrangling.

The architecture follows a battle tested pattern I've run in production: an AI agent writes through
Postgres, PowerSync replicates the changes, and the UI reacts to the local replica 

**Stack:** Django REST + Postgres · PowerSync · TanStack DB / React · pydantic-ai

---

# Conversational demo

https://github.com/user-attachments/assets/174e8957-ae7c-495c-b709-e7a712fe1789

<img width="1354" height="603" alt="screenshot" src="https://github.com/user-attachments/assets/486f0434-9da5-4892-9329-afee4acaf213" />

Demo on how to register,purchase,sell and get info on inventory

----

## Setup

Everything you need to run this on your machine.

### Prerequisites

| Tool | Why |
|------|-----|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) (running) | Postgres, PowerSync, API |
| Node.js 18+ and npm | Frontend |
| [goose](https://github.com/pressly/goose) | DB migrations from your host |

Install goose:

```bash
brew install goose
# or: go install github.com/pressly/goose/v3/cmd/goose@latest
```

### 1. Configure environment

```bash
cd inventory
cp .env.example .env
```

Edit `.env` — **required for chat**:

```env
OPENROUTER_API_KEY=sk-or-...          # https://openrouter.ai/keys
INVENTORY_AGENT_MODEL=openrouter:deepseek/deepseek-v4-flash
```

Use `OPENROUTER_API_KEY`, not `OPENAI_API_KEY` (OpenRouter keys start with `sk-or-`).

Frontend defaults work locally; optional:

```bash
cp frontend/.env.example frontend/.env
```

### 2. Start backend services

```bash
docker compose build api    # first time only
docker compose up -d
```

Wait until containers are healthy (`docker compose ps`).

### 3. Run migrations

Postgres must be up on **localhost:5433** before this step:

```bash
./scripts/migrate.sh up
```

This creates schema, seed data, and the PowerSync publication. Check: `./scripts/migrate.sh status`

### 4. Start frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

### 5. Log in

| Field | Value |
|-------|-------|
| Email | `demo@inventory.local` |
| Password | `password123` |

### Ports

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/api/docs/ |
| PowerSync | http://localhost:2000 |
| Postgres (app) | `localhost:5433` |

### Reset demo data

```bash
./scripts/reset-db.sh
```

Wipes the DB volume, re-runs migrations, restarts the stack. Log out and back in to clear local sync cache.

### Troubleshooting

| Problem | Fix |
|---------|-----|
| `goose not found` | Install goose (see Prerequisites) |
| API won't start | `docker compose logs api` — often a bad `.env` or missing migration |
| Chat returns API key error | Fix `OPENROUTER_API_KEY` in `.env`, then `docker compose up -d api` |
| Dashboard empty after login | Log out → log in (clears stale PowerSync SQLite) |
| Migrations fail | Ensure Postgres is healthy: `docker compose ps` |

### Seed data (after migrate)

| SKU | Stock | Notes |
|-----|-------|-------|
| A | 0 | $900 profit (bought 100 @ $100, sold 100 @ $10) |
| CB-01 | 400 | Craft Beer IPA — chat PO demo |
| OL-01 | 24 | Olive Oil EVOO |

---

## Architecture

One write path through Django (validation + ledger), one read path through PowerSync
(server → local SQLite → reactive UI). The two never cross: the UI never REST-fetches
display data, and writes never touch the read cache.

```
┌──────────────────────────── BROWSER ────────────────────────────-┐
│                                                                  │
│  React UI                                                        │
│   ├─ useDashboard()      ─┐                                      │
│   ├─ usePurchaseOrders() ─┤ reactive reads                       │
│   ├─ useChatMessages()   ─┘                                      │
│   │                         │                                    │
│   │                    ┌────▼─────────────────┐                  │
│   │                    │  Local SQLite        │  ← PowerSync     │
│   │                    │                      │    replica       │
│   │                    └────▲─────────────────┘                  │
│   │                         │ live queries re-run on any change  │
│   └─ REST writes            │                                    |
│      (create PO/SO,         │   chat write                       │
│       product, stock)       │            │                       │
└─────────┬───────────────────┼────────────┼──────────────────────-┘
          │ JWT                │ sync       │ CRUD upload
          ▼                    ▼            ▼
   ┌─────────────┐      ┌─────────────┐  POST /api/sync/mutations/
   │ Django REST │      │  PowerSync  │     (chat_message only)
   │  /api/...   │      │  service    │            │
   │             │      │  :2000      │            ▼
   │ services/   │      └──────▲──────┘     ┌──────────────┐
   │ inventory.py│             │ logical    │ pydantic-ai  │
   └──────┬──────┘             │ replication│ agent (loop) │
          │ SQL                │            └──────┬───────┘
          ▼                    │                   │ tools call services/
   ┌──────────────────────────-┴───────────────────▼──────────────-┐
   │                     Postgres  (db_inventory)                  │
   │   product · purchase_order · sales_order · stock_movement     │
   │   chat_message · views (product_financials_view)              │
   └──────────────────────────────────────────────────────────────-┘
```

| Layer | Path | Role |
|-------|------|------|
| Schema | `migrations/` | Goose owns DDL; Django models are `managed=False` |
| REST API | `backend/inventory_api/` | DRF + JWT; validation only, logic in `services/` |
| Domain | `backend/services/inventory.py` | Ledger writes, oversell checks, read models |
| Agent | `backend/ai/` | pydantic-ai loop, tools, guardrails, runner |
| Sync (server) | `backend/sync_api/` | Mint PowerSync JWT + upload connector |
| Sync (engine) | `powersync/config.yaml` | Replication, auth, sync rules |
| Sync (client) | `frontend/src/sync/` | Schema, connector, collections, hooks |
| UI | `frontend/src/features/` | Mantine tables + chat |

---

## Postgres — data modelling

Schema is in `migrations/` (Goose), applied **before** Django. Django never runs DDL.

**Event-sourced stock.** There is no `quantity` column on `product`. Stock is an
append-only ledger:

```
stock_movement(quantity_delta, source, source_id, unit_cost, ...)
   +100  PURCHASE_ORDER  → po_id
   -100  SALES_ORDER     → so_id
    +12  MANUAL          → null

on_hand = SUM(quantity_delta) per (user_id, product_id)
```

Order edits/deletes never mutate ledger rows — they append a **compensating** movement.
The ledger is the audit log; the current number is always a fold over it.

**Read models are views, not columns.** `product_financials_view` (migration `000006`)
joins the ledger + orders into one per-SKU row: stock on hand, qty bought/sold,
cost, revenue, profit. Financials are SQL, never LLM arithmetic.

**Conventions worth knowing:**
- **Timestamp-embedded ids** — `gen_random_with_timestamp_id()` (snowflake-ish), not bare serials. Sortable by creation, k-sortable across tables.
- **Per-user isolation** — every table carries `user_id`; owner triggers reject cross-user order/movement inserts at the DB layer.
- **Idempotent writes** — `purchase_order`/`sales_order` have a `guid` with `ON CONFLICT DO NOTHING` (safe retries).
- **Snowflake ids serialize as text** — JS `number` loses precision past 2^53, so sync rules cast every bigint to `::text`.

---

## PowerSync — the sync engine

PowerSync replicates user-scoped Postgres rows down to an in-browser SQLite database
over a websocket, and ships local writes back up through a connector. It is the **only**
source of display data on the client.

**Down (server → client).** `powersync/config.yaml` defines one bucket parameterised by
the authenticated user:

```yaml
bucket_definitions:
  inventory:
    parameters: SELECT request.user_id() AS user_id   # from the PowerSync JWT
    data:
      - SELECT ... FROM product          WHERE user_id::text = bucket.user_id
      - SELECT ... FROM purchase_order   WHERE user_id::text = bucket.user_id
      - SELECT ... FROM sales_order      WHERE user_id::text = bucket.user_id
      - SELECT ... FROM stock_movement   WHERE user_id::text = bucket.user_id
      - SELECT ... FROM chat_message     WHERE user_id::text = bucket.user_id
```

Postgres `wal_level=logical` + a `powersync` publication (migration `000005`) stream
changes; PowerSync incrementally pushes only the diff. Sync rules can't `JOIN`/`GROUP BY`,
so **base tables replicate, aggregates are computed client-side** (see Frontend below).

**Up (client → server).** Reads and writes use different doors on purpose:
- **Inventory writes** (product, PO, SO, manual stock) go through **Django REST** — they need oversell checks, ledger side effects, and validation that don't belong on the client.
- **Chat writes** ride the **PowerSync upload connector**: an optimistic insert into the local `chat_message` collection → `POST /api/sync/mutations/` → the server runs the agent and inserts the assistant reply → it replicates back down.

**Auth.** `POST /api/auth/login/` → Django JWT. `POST /api/sync/token/` mints a short
PowerSync JWT (HS256) whose `user_id` claim drives bucket scoping. Keys must match
between `backend/sync_api/jwt.py` and `powersync/config.yaml`.

**Two Postgres databases.** The app DB (`db_inventory`) holds your tables and logical
replication. A separate PowerSync DB (`db_powersync`) stores sync buckets and checkpoint
state — both run in `docker-compose.yml`.

---

## Frontend

Two reactive read styles, both reading the **same local SQLite replica**, never the network:

```
PowerSync replica (SQLite)
        │
        ├── @powersync/react  useQuery(SQL)         → useDashboard, usePurchaseOrders,
        │      raw SQL, multi-table aggregates         useSalesOrders, useStockMovements
        │      (GROUP BY / JOIN / decimal coercion)
        │
        └── @tanstack/react-db  useLiveQuery         → useChatMessages
               typed collection + optimistic inserts
```

- **TanStack DB** wraps the `chat_message` table as a typed, reactive collection
  (`@tanstack/powersync-db-collection`, eager sync). Chat sends are **optimistic**:
  `collection.insert(...)` paints the user bubble instantly, then the connector uploads
  and the assistant reply streams back in — all through the same live query.
- **Raw `@powersync/react` `useQuery`** handles the dashboard, because the per-SKU
  financials row is a multi-table aggregate over decimal-as-text columns. SQLite does the
  `GROUP BY` + coercion that a query-builder can't (`frontend/src/sync/queries.ts`
  mirrors `product_financials_view`).
- **TanStack Query** (`useInventory.ts`) is used *only* for REST write mutations. The
  mutations deliberately do **not** invalidate anything — see below.

---

## AI — the agent

A pydantic-ai `Agent` (`backend/ai/agent.py`) runs an agentic tool loop in-process inside
Django. Model is pluggable via `INVENTORY_AGENT_MODEL` (OpenRouter / DeepSeek / Gemini /
OpenAI).

```
user msg ─▶ check_input() ─▶ Agent loop ──┬─ calculator
            (input guard)   (≤5 retries)   ├─ register_product   ┐
                  │                         ├─ create_purchase_order│
                  │                         ├─ record_sale          ├─ services/inventory.py
                  │                         ├─ add_stock            │  (real DB writes)
                  │                         ├─ query_stock          │
                  │                         └─ get_profit          ┘
                  ▼                              │
            output_guardrails_handler ◀──────────┘
            (figure guard) ─▶ assistant reply ─▶ chat_message ─▶ syncs to client
```

**Tools do the work, not the prose.** Every mutation and every figure goes through a tool
that calls `services/inventory.py`. The model never invents stock levels or does mental
math — there's a `calculator` tool for arithmetic.

**Guardrails** (`backend/ai/guardrails.py`):
- *Input* — reject empty / over-length / prompt-injection (`ignore previous instructions`, role-swap, prompt-exfil) before the model sees it.
- *Output figure guard* — if a reply states a number (`$200`, `500 units`, a margin) for a stock/financial question but **no data tool was called this turn**, raise `ModelRetry` with a targeted hint. Forces fresh tool data instead of hallucinated figures.
- *Write-intent skip* — purchase/sell/register commands bypass the figure guard: the model legitimately narrates "Purchase order created: 100 units…" *after* the tool runs, and the DB only ever changes through the tool anyway.

**Runner** (`backend/ai/runner.py`) — single persistent asyncio loop (pydantic-ai binds
its httpx client to the first loop it sees; WSGI threads would otherwise each spawn one).
Maps provider `401`/`429` to friendly chat replies instead of 500s. Chat blocks ~20–30s
per turn while the agent runs inside the mutation handler.

---

## PowerSync + AI = s2

The hard part of an AI that mutates data is keeping the UI honest. The agent might create
a PO, record a sale, *and* register a product in one turn. How to update the dashboard?

One option, **The cache-invalidation approach**: after the agent runs, return the
set of affected resources so the client can invalidate them (like agent returning set o query keys so that React query invalidates them)

```
agent reply: { text: "...", invalidate: ["products", "stock", "financials"] }
            └─▶ queryClient.invalidateQueries(["products"])  // and stock, and financials
            └─▶ each refetch round-trips to REST
```

This is brittle: the agent (or you) must enumerate every cache key every tool touches; a
missed key shows stale data; an over-broad key refetches the world; and a sale that
changes stock *and* profit must remember to list both. The LLM becomes responsible for
cache coherence

**The PowerSync approach**: the database is the single source of truth, and
changes flow downhill automatically.

```
agent tool writes Postgres
   └─▶ logical replication → PowerSync → local SQLite changes
        └─▶ every useQuery / useLiveQuery over those tables re-runs
             └─▶ dashboard, orders, stock, chat all update — no invalidate, no refetch
```

The agent returns *only* a reply. It never says what changed, because nothing needs to be
told — the reactive read layer observes the data, not the operation. Same property covers
**offline** (writes queue, sync on reconnect) and **multi-tab / multi-device** (every
client converges on the same replica). This is why `useInventory.ts` mutations have no
`onSuccess: invalidate` — and the comment there says exactly that.

---

## Improvements

- **Chat** — render markdown in assistant bubbles; today some answers could have breaklines, better markdown handling;
- **AI latency** — async agent (202 + background job), streaming or filler messages while tools run.
- **UI** — `$` / `%` formatting, financials on product detail, better loading states.
- **Backend** — structured logs, traces, health endpoint, agent isolated from WSGI.

---

## Tests

```bash
cd backend && pytest        # services, REST, guardrails (skips if Postgres is down)
```

Guardrail logic and the ledger math each leave a runnable check behind
(`tests/test_guardrails.py`, `tests/test_services.py`).

API docs: http://localhost:8000/api/docs/ · endpoint list: [backend/README.md](backend/README.md)
