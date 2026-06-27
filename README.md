# Inventory

Conversational inventory management for F&B/CPG brands. Chat with an LLM agent
("buy 100 units of CB-01 for $200") and watch a live dashboard update — offline-capable,
no manual refresh, no cache wrangling.

The architecture follows a battle tested pattern I've run in production: an AI agent writes through
Postgres, PowerSync replicates the changes, and the UI reacts to the local replica 

**Stack:** Django REST + Postgres · PowerSync · TanStack DB / React · pydantic-ai

-----

# Conversational demo



https://github.com/user-attachments/assets/83355409-345d-436e-b958-1b87327e4600



https://github.com/user-attachments/assets/bc7b893b-5fb5-4872-ad8d-79c59468e92e




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

Edit `.env` — **required for chat**:

```env
OPENROUTER_API_KEY=sk-or-...          # https://openrouter.ai/keys
INVENTORY_AGENT_MODEL=openrouter:openai/gpt-4o
```

Use `OPENROUTER_API_KEY`, not `OPENAI_API_KEY` (OpenRouter keys start with `sk-or-`).

### 2. Start backend services

```bash
docker compose build api   
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

## Architecture

One write path through Django (validation + ledger), one read path through PowerSync
(server → local SQLite → reactive UI). The two never cross: the UI never REST-fetches
display data, and writes never touch the read cache.

```
┌──────────────────────────── BROWSER ────────────────────────────-┐
│                                                                  │
│  React UI                                                        │
│   ├─ useDashboardRead()  ─┐  (hoisted — one subscription on / + /products)
│   ├─ usePurchaseOrders() ─┤  flat SELECTs on local SQLite
│   ├─ useChatMessages()   ─┘
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
   │   product_financials_summary · chat_message · views           │
   └──────────────────────────────────────────────────────────────-┘
```

| Layer | Path | Role |
|-------|------|------|
| Schema | `migrations/` | Goose owns DDL; Django models are `managed=False` |
| REST API | `backend/inventory_api/` | DRF + JWT; validation only, logic in `services/` |
| Domain | `backend/services/inventory.py` | Ledger writes, oversell checks, read models |
| Agent | `backend/ai/` | pydantic-ai loop, tools, guardrails, runner |
| Sync (server) | `backend/sync_api/` | Mint PowerSync JWT + upload connector |
| Sync (engine) | `powersync/config.yaml` | Replication, auth, sync streams (edition 3) |
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

**Read models on Postgres, flat rows on the client.** Trigger-maintained
`product_financials_summary` (migration `000007`) holds per-SKU stock, cost,
revenue, profit, and margin. Triggers on `product`, orders, and `stock_movement`
keep it current; `product_financials_view` is a thin wrapper for REST/AI.
Denormalized `product_sku` / `product_name` on orders and movements (migration
`000008`) let the client list PO/SO/stock without JOINs — the standard
PowerSync-friendly pattern: denormalize on Postgres so each sync stream hits one flat table.

Financials are SQL, never LLM arithmetic.

**Conventions worth knowing:**
- **Timestamp-embedded ids** — `gen_random_with_timestamp_id()` (snowflake-ish), not bare serials. Sortable by creation, k-sortable across tables.
- **Per-user isolation** — every table carries `user_id`; owner triggers reject cross-user order/movement inserts at the DB layer.
- **Idempotent writes** — `purchase_order`/`sales_order` have a `guid` with `ON CONFLICT DO NOTHING` (safe retries).
- **Snowflake ids serialize as text** — JS `number` loses precision past 2^53, so sync streams cast every bigint to `::text`.

---

## PowerSync — the sync engine

PowerSync replicates user-scoped Postgres rows down to an in-browser SQLite database
over a websocket, and ships local writes back up through a connector. It is the **only**
source of display data on the client.

**Down (server → client).** `powersync/config.yaml` defines one user-scoped [sync stream](https://docs.powersync.com/sync/streams/overview) with `auto_subscribe: true` (same “sync everything on connect” behavior as the old bucket):

```yaml
config:
  edition: 3

streams:
  inventory:
    auto_subscribe: true
    queries:
      - SELECT ... FROM product_financials_summary WHERE user_id::text = auth.user_id()
      - SELECT ... FROM purchase_order        WHERE user_id::text = auth.user_id()  -- includes product_sku, product_name
      - SELECT ... FROM sales_order           WHERE user_id::text = auth.user_id()
      - SELECT ... FROM stock_movement        WHERE user_id::text = auth.user_id()
      - SELECT ... FROM chat_message          WHERE user_id::text = auth.user_id()  -- last 100 rows (CHAT_SYNC_LIMIT)
```

Postgres `wal_level=logical` + a `powersync` publication (migration `000005`, extended
in `000007`) stream changes; PowerSync incrementally pushes only the diff. Stream
queries target **flat tables** — no JOIN/GROUP BY in sync config; aggregation and
denormalization live on Postgres via triggers.

**Up (client → server).** Reads and writes use different doors on purpose:
- **Inventory writes** (product, PO, SO, manual stock) go through **Django REST** — they need oversell checks, ledger side effects, and validation that don't belong on the client.
- **Chat writes** ride the **PowerSync upload connector**: an optimistic insert into the local `chat_message` collection → `POST /api/sync/mutations/` → the server runs the agent and inserts the assistant reply → it replicates back down.

**Auth.** `POST /api/auth/login/` → Django JWT. `POST /api/sync/token/` mints a short
PowerSync JWT (HS256) whose `sub` claim is the user id (`auth.user_id()` in streams). Keys must match
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
        ├── @powersync/react  useQuery(SQL)         → useDashboardRead, usePurchaseOrders,
        │      flat SELECT on summary + denorm cols   useSalesOrders, useStockMovements
        │
        └── @tanstack/react-db  useLiveQuery         → useChatMessages
               typed collection + optimistic inserts
```

- **TanStack DB** wraps the `chat_message` table as a typed, reactive collection
  (`@tanstack/powersync-db-collection`, eager sync). Chat sends are **optimistic**:
  `collection.insert(...)` paints the user bubble instantly, then the connector uploads
  and the assistant reply streams back in — all through the same live query.
- **Raw `@powersync/react` `useQuery`** handles inventory reads: dashboard reads
  `product_financials_summary`; order/movement lists read denormalized columns — no
  client-side JOIN or GROUP BY (`frontend/src/sync/hooks.ts`).
- **`DashboardReadProvider`** hoists `useDashboard` so `/` and `/products` share one
  reactive subscription across navigation.
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
Maps provider `401`/`429` to friendly chat replies instead of 500s. Upload handler
persists the user message + thinking placeholder, then **`schedule_coro`** runs the
agent on the background loop — HTTP returns in under a second; the LLM turn (~20–30s)
completes asynchronously and the assistant row replicates down.

See **[Improvements](#improvements-roadmap-to-production-scale)** for the path
toward production-grade AI orchestration (Temporal, skills, expanded guardrails).

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

## Improvements (roadmap to production scale)

This demo follows a **production-shaped architecture** at portfolio scope: Postgres as
truth, PowerSync for offline-first reads, tools that own mutations, guardrails that block
hallucinated figures, and **server-maintained read models** synced as flat rows. The
tables below map what exists today, what a full-scale mobile + banking stack would add,
and the sequenced work to close the gap without a big-bang rewrite.

Deep dives: [AI layer comparison](docs/inventory_vs_octopus_ai.md) · [PowerSync read patterns](docs/powersync_reads_and_octopus_patterns.md) · [architecture target doc](docs/ARCHITECTURE_CURRENT_AND_TARGET.md)

### North star (patterns we are converging on)

| Pattern | Production ideal | Inventory today |
|---------|------------------|-----------------|
| Display reads | Local SQLite via PowerSync — **no REST refetch on navigation** | ✅ Same |
| Write path | Service layer + durable workflows at scale | ✅ Django `services/` + REST; chat via sync mutations |
| Read models | Trigger-maintained summary tables + denormalized sync columns | ✅ `product_financials_summary` + denorm labels |
| Sync queries | Flat `SELECT … WHERE` per table; no JOIN in stream config | ✅ Mostly; see pagination/window gaps below |
| Volume control | Session-scoped chat, time partitions, cursor pagination | ⏳ Partial — chat capped at 100 rows |
| AI | pydantic-ai + tools + guardrails; durable workflow for chat turns | ✅ Same philosophy; in-process agent, no Temporal yet |

Navigation and cache invalidation are **already correct** — a production app would not
change that story. The remaining work is **what gets synced**, **how much history the
client holds**, and **how durable/scalable the agent runtime is**.

### Read path & PowerSync — sequenced priority

Work in this order. Each step is independently shippable.

| Priority | Item | Status | What it does | Production precedent |
|----------|------|--------|--------------|----------------------|
| **1** | Server summary + denorm tables | ✅ Done | `product_financials_summary` (triggers on ledger/orders); `product_sku`/`product_name` on PO/SO/movements | Daily balance rollups, merchant aggregates, payment-row denorm |
| **2** | Hoist `useDashboard` | ✅ Done | `DashboardReadProvider` — one subscription for `/` + `/products` | Single layout-level DB subscription in app shell |
| **3** | Chat sync cap (50–100 rows) | ✅ Done | Stream syncs last **100** rows (`CHAT_SYNC_LIMIT`); agent still loads **5** turns for LLM context | Session/window bounds on messaging sync |
| **4** | PO/SO/movement **local** LIMIT + load-more | ⏳ Next | `ORDER BY … DESC LIMIT 50` in hooks; "Load more" from local SQLite cursor | Cursor pagination on local reads (`WHERE id > ? LIMIT N`) |
| **5** | **90-day sync window** on orders/movements | ⏳ Planned | Cap replication in `powersync/config.yaml` (`WHERE created_at >= now() - interval '90 days'`) | Time-bounded payment/order partitions |
| **6** | Session-scoped chat + yearly partitions | ⏳ If product grows | JWT `chat_session_id` bucket; yearly partition wildcards on `chat_message` | Session-scoped messaging buckets, `*_20%` partition streams |

**Why this order:** (1–3) remove the worst client/sync cost at demo scale. (4) bounds UI work without changing replication. (5) bounds device storage and initial sync. (6) only matters beyond a single-thread chat demo or years of order history.

**Dual-bucket rule:** keep syncing **base tables** for writes and audit, plus **summary/rollup tables** for dashboards. Do not drop raw `purchase_order` / `stock_movement` rows until a rollup bucket replaces a screen entirely.

### AI architecture — sequenced toward production agent platform

Inventory AI is a **minimal solo agent**: pydantic-ai loop, tools call the real write path,
figure guardrails, calculator for arithmetic. A production banking agent adds durable
workflows, skills, and richer guardrails.

| Priority | Item | Status | Production target | Notes |
|----------|------|--------|-------------------|-------|
| **A** | Tools → `services/inventory.py` facade | ✅ Done | Tools → durable workflow → service API | Single write path for REST + chat |
| **B** | Figure + write-intent guardrails | ✅ Done | Multi-category output guardrails | Current guardrails cover SKU/profit domain |
| **C** | Async agent after upload | ✅ Partial | Durable chat-turn workflow | `schedule_coro` — HTTP returns fast; agent still in-process |
| **D** | Tool idempotency (`tool_guid`) | ✅ Partial | Workflow idempotency keys | PO/SO done; extend to `add_stock`, `register_product` |
| **E** | Durable chat turn job | ⏳ Planned | Temporal worker + activity | Celery/RQ acceptable in monolith; Temporal if multi-service |
| **F** | Skills + nested toolsets | ⏳ Planned | Skill-aware, feature-controlled toolsets | When tool count / prompt token cost grows |
| **G** | Expanded guardrails | ⏳ Planned | Task hallucination, tag validation, URL allowlists | Split `guardrails.py` → package |
| **H** | Structured output (rich blocks) | ❌ Defer | Protobuf + channel adapters | Markdown chat is fine until rich messaging UI |
| **I** | Dynamic model routing | ❌ Defer | Feature-flag model racing | Single `INVENTORY_AGENT_MODEL` is enough for demo |

**Agent history alignment:** server loads **5** non-placeholder turns (`CHAT_HISTORY_LIMIT`); client syncs **100** rows (`CHAT_SYNC_LIMIT`) for UI scrollback. Production would add session-scoped sync buckets before unbounded chat history.

**Interview one-liner:**

> pydantic-ai agent — tools call the real write path, guardrails enforce fresh data before numbers, UI reacts to Postgres via PowerSync — without Temporal, skills, or structured message blocks.

### What we explicitly defer (still valid for a portfolio demo)

- Multi-service split (AI worker vs Django API)
- PowerSync Cloud / RS256 JWT production hardening
- WhatsApp / rich channel message formatting
- Multi-agent intent routing (inventory uses one solo agent)
- Yearly table partitions until order volume warrants it

### Related docs

| Doc | Contents |
|-----|----------|
| [docs/inventory_vs_octopus_ai.md](docs/inventory_vs_octopus_ai.md) | Side-by-side AI layer comparison |
| [docs/powersync_reads_and_octopus_patterns.md](docs/powersync_reads_and_octopus_patterns.md) | Read models, navigation, sync patterns at scale |
| [docs/ARCHITECTURE_CURRENT_AND_TARGET.md](docs/ARCHITECTURE_CURRENT_AND_TARGET.md) | Phased target architecture |
| [docs/inventory_exam.md](docs/inventory_exam.md) | Q14–Q15 on trigger denorm + summary tables |

---

## Tests

```bash
cd backend && pytest        # services, REST, guardrails (skips if Postgres is down)
```

Guardrail logic and the ledger math each leave a runnable check behind
(`tests/test_guardrails.py`, `tests/test_services.py`).

API docs: http://localhost:8000/api/docs/ · endpoint list: [backend/README.md](backend/README.md)

