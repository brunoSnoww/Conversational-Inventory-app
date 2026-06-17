# Interview Guide — Conversational Inventory App

Use this document to walk through the project live. Each section answers **what we built**,
**why we chose it**, and **what we'd say if challenged**.

---

## 30-second pitch

> "Inventory management for F&B brands with a chat interface. You can say 'buy 100 units of
> CB-01 for $200' and the dashboard updates without refresh. The AI writes through Postgres,
> PowerSync replicates to the browser, and React reacts to a local SQLite copy. Business rules
> live in one Python service layer — the LLM never does math or mutates data directly."

---

## 1. Requirements mapping

The take-home spec (`NEW_PROJECT.md`) asked for:

| Requirement | How we satisfy it |
|-------------|-------------------|
| Register products (name, SKU, units) | REST + forms + agent `register_product` tool |
| Stock via manual add or purchase order | `stock_movement` ledger + PO endpoint |
| Unique stock identifier | `stock_movement_id` (snowflake PK) |
| Sales orders with qty + unit price | `sales_order` + compensating ledger entries |
| Financials: cost, revenue, profit, margin | `product_financials_view` (SQL, not LLM) |
| Product A scenario ($100 → $1000 → $900) | Seed migration + pytest assertions |
| Django + DRF + Postgres | ✓ |
| React + Mantine + TanStack Query | ✓ (Query for **writes**; see §4) |
| Auth + per-user isolation | JWT + `user_id` on every row + sync rules |
| Tests | pytest (backend) + vitest (frontend markdown) |
| Docker | `docker-compose.yml` + `docker-compose.prod.yml` |

**Honest tension:** the spec says "all data fetched from Django API." We deliberately use
PowerSync for **reads** because an AI that mutates data makes cache invalidation brittle.
We explain this as an architectural upgrade, not a shortcut (§4).

---

## 2. System architecture (one diagram to draw)

```
┌──────────────────────────── BROWSER ────────────────────────────┐
│  React + Mantine                                                 │
│   ├─ reads  → PowerSync useQuery / TanStack DB useLiveQuery     │
│   │           (local SQLite replica)                             │
│   └─ writes → Django REST (forms) + chat upload (mutations)     │
└─────────┬───────────────────────────────┬───────────────────────┘
          │ JWT REST                       │ WebSocket sync
          ▼                                ▼
   ┌─────────────┐                  ┌─────────────┐
   │ Django API  │                  │  PowerSync  │
   │ + pydantic  │                  │  service    │
   │   AI agent  │                  └──────▲──────┘
   └──────┬──────┘                         │ logical replication
          │ SQL                             │
          ▼                                 │
   ┌──────────────────────────────────────┴──────┐
   │              Postgres (db_inventory)           │
   │  product · orders · stock_movement · chat     │
   └─────────────────────────────────────────────┘
```

**Key invariant:** two doors on purpose.

- **Writes** → Django (validation, ledger rules, oversell checks, agent tools).
- **Reads** → PowerSync replica (reactive UI, no manual refetch).

They never cross.

---

## 3. Data modeling decisions

### 3.1 Event-sourced stock ledger (not a `quantity` column)

**What:** `product` has no stock column. Every change is an append-only row in
`stock_movement` with `quantity_delta` (+100 purchase, −10 sale, +12 manual).

**Why:**

- **Audit trail** — you can explain every unit change (source: PO, SO, manual).
- **Corrections** — edit/delete orders append *compensating* movements; history stays intact.
- **Single formula** — on-hand = `SUM(quantity_delta)` per `(user_id, product_id)`.

**Say in interview:** "Stock is derived, not stored. Same pattern as financial ledgers in
banking — events are truth, balances are projections."

**Alternative rejected:** `UPDATE product SET quantity = quantity + 10`. Simpler but loses
history and makes concurrent edits dangerous.

### 3.2 SQL views for financials (not LLM math)

**What:** `product_financials_view` joins ledger + orders → cost, revenue, profit, margin per SKU.

**Why:** The spec's Product A example ($900 profit, 900% margin) must be **exact**. LLMs
hallucinate numbers. Agent tools call `get_profit` which hits this view.

**Demo line:** "If the chat says profit is $900, it's because `get_profit` ran — not because
the model calculated it."

### 3.3 Goose migrations, Django `managed=False`

**What:** Schema lives in `migrations/*.sql` (Goose). Django models are read-only mirrors.

**Why:**

- SQL-first control (enums, triggers, publications, views) in one place.
- PowerSync publication (`powersync`) is a migration, not an afterthought.
- Matches how I'd run Postgres in production — migrations before app code.

**Tradeoff:** two tools (Goose + Django). Worth it for ledger triggers and replication setup.

### 3.4 Timestamp-embedded IDs (snowflakes)

**What:** `gen_random_with_timestamp_id()` — time-sortable 64-bit BIGINTs, cast to `text` in
sync rules (JS `Number` loses precision past 2⁵³).

**Why:** Sortable PKs without a separate `created_at` index; k-sortable across tables.

### 3.5 Per-user isolation at every layer

**What:** Every table has `user_id`. DB triggers reject cross-user order/movement inserts.
API filters on `request.user.user_id`. PowerSync bucket: `WHERE user_id = bucket.user_id`.

**Test:** `test_user_isolation_api` — user A's SKU invisible to user B.

---

## 4. PowerSync — the biggest architectural bet

### 4.1 Problem we're solving

When the AI creates a PO, records a sale, and registers a product in **one chat turn**, how
does the dashboard know what to refresh?

**Naive approach (rejected):**

```json
{ "reply": "Done.", "invalidate": ["products", "stock", "financials"] }
```

Brittle: agent must enumerate cache keys; missed key = stale UI; LLM bad at bookkeeping.

**Our approach:**

```
Agent tool → INSERT Postgres → logical replication → PowerSync → local SQLite changes
→ every watched query re-runs → UI updates automatically
```

The agent returns **only text**. It never tells the client what changed.

### 4.2 Why PowerSync specifically

- **Offline-capable** — writes queue, sync on reconnect (bonus beyond spec).
- **Multi-tab** — same user, same replica, converges automatically.
- **Chat as data** — `chat_message` is a synced table; assistant replies appear via replication,
  not a separate WebSocket protocol.

Pattern I've used in production: conversational UI where messages are rows, not sockets.

### 4.3 Sync rules constraint

PowerSync sync rules can't `JOIN` or `GROUP BY`. So:

- **Base tables** replicate down (`product`, orders, `stock_movement`, `chat_message`).
- **Aggregates** (dashboard financials row) computed in client SQLite (`frontend/src/sync/queries.ts`),
  mirroring `product_financials_view`.

**If asked:** "Why not sync the view?" — PowerSync rules are row-level SELECTs per table;
client-side SQL on a replica is the pragmatic read model.

### 4.4 Write path split

| Action | Path |
|--------|------|
| Create product / PO / sale / manual stock | Django REST |
| Send chat message | PowerSync upload → `POST /api/sync/mutations/` → agent |

**Why chat goes through sync:** optimistic UI — user bubble appears instantly in local SQLite;
upload triggers agent; assistant row replicates back.

**Why inventory CRUD stays REST:** oversell checks, ledger side effects, validation belong
server-side, not on client.

### 4.5 TanStack Query's role

**Writes only** (`useInventory.ts`). No `invalidateQueries` on success — PowerSync handles reads.

**If challenged on spec:** "TanStack Query is there for mutations. Reads intentionally use
PowerSync because the spec's fetch-everything-via-REST model breaks down when an AI mutates
multiple entities per turn. This is the same data, different transport."

---

## 5. AI layer decisions

### 5.1 pydantic-ai agent, in-process (not gRPC, not Temporal)

**What:** `inventory_agent` runs inside Django when a chat mutation arrives. Tools call
`services/inventory.py` — same functions as REST.

**Why in-process for this project:**

- Take-home scope — no second service to deploy.
- Agent + DB in one place — low latency for tool calls.
- Spec says Django; adding gRPC/Temporal is over-engineering here.

**Production note:** I'd extract to a worker for scale; gunicorn threads handle demo traffic today.

### 5.2 Tools do the work, not the prose

**Tools:** `register_product`, `create_purchase_order`, `record_sale`, `add_stock`,
`query_stock`, `get_profit`, `calculator`.

**Rule in prompt:** write intents → call tool first turn. Never state figures without a data tool.

**Why `calculator` tool:** forces arithmetic out of the model. Margins and totals go through code.

### 5.3 Guardrails

| Layer | What |
|-------|------|
| Input | Length cap, prompt-injection regex |
| Output figure guard | If reply contains `$`, `%`, units, profit words but no `query_stock`/`get_profit`/`calculator` this turn → `ModelRetry` |
| Write-intent skip | PO/sell/register commands skip figure guard — model may narrate after tool ran |

**Interview story:** "We had a bug where PO replies said '$200 total' and the figure guard
false-retried. Fix: skip guard when user intent is clearly a write — DB only changes via tools anyway."

### 5.4 Chat latency

Agent runs synchronously in mutation handler (~20–30s). User sees optimistic user bubble + `…`
placeholder. Tier A deploy: gunicorn threads so other API calls aren't blocked.

**Future:** background job + assistant placeholder row (documented in README Improvements).

### 5.5 Model provider

OpenRouter via env (`OPENROUTER_API_KEY`). Pluggable `INVENTORY_AGENT_MODEL`. Auto-detect
`sk-or-` keys — common footgun we handled.

---

## 6. Backend / API decisions

### 6.1 Single source of truth: `services/inventory.py`

REST views **and** AI tools call the same functions. Business rules (oversell, unit validation,
compensating movements) live once.

**Say:** "I can change oversell logic in one file; REST and chat both pick it up."

### 6.2 DRF ViewSets + OpenAPI

Router-based resources, JWT auth, `/api/docs/` for evaluators. Cursor pagination on lists.

Slight REST pragmatism: `POST /api/stock/add/` as action, `GET /api/financials/{sku}/` —
readable over pure hypermedia purity.

### 6.3 Schema ownership

Goose → Django unmanaged models. API never runs migrations. Deploy: `docker compose up` then
`./scripts/migrate.sh up`.

---

## 7. Frontend decisions

### 7.1 Mantine for UI

Tables (`Table.data`, sticky headers, scroll containers), forms, layout shell. No Tailwind —
Mantine covers the spec; less CSS surface area.

### 7.2 Two reactive read patterns, one SQLite replica

| UI area | Hook | Why |
|---------|------|-----|
| Dashboard, orders, stock | `@powersync/react` `useQuery` | Multi-table SQL aggregates |
| Chat | `@tanstack/react-db` `useLiveQuery` | Optimistic inserts on send |

### 7.3 Chat markdown rendering

Assistant bubbles parse markdown (`marked`, `breaks: true`) + WhatsApp-style `*bold*` conversion
(ported from a production chat UI). User bubbles stay plain text.

### 7.4 Auth flow

Login → JWT in memory/localStorage → PowerSync init with `user_id` → per-user SQLite file.
Logout wipes PowerSync + storage (prevents stale replica on re-login).

---

## 8. Security talking points

| Concern | Mitigation |
|---------|------------|
| Data isolation | `user_id` in SQL, API, sync rules, mutation handler checks |
| Auth | JWT on all API routes; PowerSync token minted server-side |
| Agent safety | Tools-only mutations; figure guard on reads |
| Secrets | `.env` gitignored; dev HS256 PowerSync key documented for local only |
| Prod | `docker-compose.prod.yml`: gunicorn, `DEBUG=false`, strong secrets required |

**Weakness to acknowledge:** chat blocks a worker thread; no rate limiting on agent yet.

---

## 9. Live demo script (~5 minutes)

1. **Login** — `demo@inventory.local` / `password123`
2. **Dashboard** — show SKU A ($900 profit, 0 stock), CB-01 (400 units), OL-01
3. **Products** — click SKU → detail with financials columns
4. **Manual flow** — create product or add stock via form (REST write → sync updates table)
5. **Chat** — *"Create a purchase order for 100 units of CB-01 at $200 total"*
   - Point out: user bubble instant, ~25s wait, dashboard CB-01 stock 400 → 500 without refresh
6. **Purchases / Activity** — new PO visible in synced tables
7. **Optional** — *"What's my profit on product A?"* → agent calls `get_profit`

**If chat fails:** check `OPENROUTER_API_KEY` in `.env`, restart API container.

**If dashboard empty:** log out and back in (stale PowerSync cache).

---

## 10. Likely interview questions

### "Why PowerSync instead of TanStack Query for everything?"

AI mutates multiple tables per turn. Cache invalidation requires the model to know what changed.
Database replication pushes diffs; watched queries re-run. Same mechanism for offline and multi-tab.

### "Why not put stock quantity on the product row?"

Ledger gives audit trail and safe corrections. On-hand is always `SUM(movements)` — one source of truth.

### "How do you prevent the LLM from inventing profit numbers?"

Three layers: prompt (tools first), output figure guard (`ModelRetry`), and `get_profit` hitting SQL views.

### "Why Goose instead of Django migrations?"

Publication, triggers, views, and enums in SQL. PowerSync setup is migration 000005, not a manual step.

### "How is this different from ChatGPT + spreadsheet?"

ChatGPT doesn't write to your DB with validation. Here every mutation goes through `services/inventory.py`
with oversell checks and ledger rules. UI stays in sync via replication, not copy-paste.

### "What would you do for production?"

- Async agent job (off WSGI thread)
- PowerSync Cloud or managed Postgres with logical replication
- RS256/JWKS for PowerSync auth
- Structured logging, health checks, rate limits
- `$` / `%` formatting in UI

### "What did you cut for scope?"

- PO/SO edit UI (API supports it)
- User registration UI (API has `/auth/register/`)
- E2E Playwright tests
- Full async chat streaming

---

## 11. Tests as proof

```bash
cd backend && pytest     # Product A scenario, isolation, ledger compensating entries, guardrails
cd frontend && npm test  # Markdown render, ChatMessageBody
```

Highlight: `test_example_scenario_via_api` proves $100 / $1000 / $900 / 900% margin end-to-end.

---

## 12. One-slide summary (if they want a closing line)

> **Postgres is truth. Django enforces rules. PowerSync delivers truth to the browser.
> The agent is a controlled writer, not a calculator. The UI reacts to data, not to prompts.**

That is the through-line of every major decision in this project.

---

## Practice exam

Before the interview, work through **[docs/inventory_exam.md](docs/inventory_exam.md)** (12 questions,
90 minutes, open codebase). Check your work against **[docs/inventory_exam_answers.md](docs/inventory_exam_answers.md)**.
