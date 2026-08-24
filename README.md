# FantaMazor

A decision-support system for Fantacalcio (Italian fantasy football): player database, a proprietary FantaScore, and a live auction advisor that never lets you bid your way into an incomplete roster.

This is **MVP1** — see [Scope](#scope-mvp1) for exactly what's built and what's deferred.

## Architecture overview

Two separate apps, communicating over REST:

```
FantaMazor/
  backend/    FastAPI (Python) — all data, scoring, and auction logic. Owns the database.
  frontend/   Next.js (TypeScript, App Router) — the UI. Talks only to the backend API.
```

Backend was chosen as Python specifically so the scoring/ML work in later phases (§42/§43 backtesting, model training) has a natural home, without the frontend needing to change.

### Provider architecture (§39)

Neither the database nor the frontend ever calls an external API directly. Everything goes through an interface in `backend/app/providers/base.py`:

| Interface | MVP1 implementation | Status |
|---|---|---|
| `FantasyDataProvider` (listone/FVM) | `ManualImportProvider` (CSV/JSON upload), `DemoDataProvider` (seed data) | ✅ implemented |
| `PlayerDataProvider` (structured player/team data) | `ApiFootballProvider` | ✅ implemented, but reports itself `unavailable` until `API_FOOTBALL_API_KEY` is set |
| `AuctionDataProvider` (market-average benchmark) | — | local `auction_transactions` history used directly instead |
| `MatchDataProvider`, `InjuryDataProvider`, `LineupDataProvider`, `AdvancedStatsProvider` | — | interfaces declared, deferred to MVP2 |

Swapping in a real Fantacalcio.it/Understat integration later means adding a new class here — no changes to the database schema, the scoring engine, or the frontend.

### Data flow

```
Listone (CSV/JSON) or demo seed
        │
        ▼
ManualImportProvider / DemoDataProvider  →  player entity resolution (§8/§9)
        │                                    (normalized-name + role match;
        ▼                                     see app/ingestion/player_resolution.py)
fantasy_quotes  (DB)
        │
        ▼
Scoring pipeline (POST /api/data/score)
        │  role-specific weighted model → app/scoring/fanta_score.py
        ▼
player_scores, player_tiers  (DB, versioned by model_version)
        │
        ▼
Auction engine (app/auction/*)  ──►  ModelAuctionValue, RecommendedPrice,
        │                             MaximumBid (hard-capped by budget invariant)
        ▼
/auction/live  (frontend)
        │
        ▼
auction_transactions  (DB) ──► feeds back into local market-average signal
```

### Database (PostgreSQL via SQLAlchemy + Alembic)

MVP1 tables (see `backend/app/db/models.py`): `users`, `league_settings`, `league_members`, `teams`, `seasons`, `players`, `player_external_ids`, `fantasy_quotes`, `player_season_stats`, `data_sources`, `data_sync_logs`, `model_versions`, `player_scores`, `player_tiers`, `auction_sessions`, `auction_transactions`, `league_rosters`.

The rest of the full §40 table list (`injuries`, `suspensions`, `lineups`, `news`, `formation_recommendations`, `trade_analysis`, `alerts`, ...) is deferred to MVP2/3 and intentionally **not** created yet — no empty unused tables.

JSON columns use a Postgres-JSONB-in-production / plain-JSON-elsewhere type (`PortableJSON` in `models.py`), so the schema is exercisable against SQLite for quick local testing without losing JSONB in the real deployment.

### Scoring methodology (§11-13)

**FantaScore v1** is deterministic, not ML (§42 — earn the right to add ML via backtesting first). For each role, every input feature (fantasy average, average rating, goals, assists, appearances, FVM) is min-max normalized across the current player pool, then combined with role-specific weights from `backend/app/scoring/model_config.py`. A player missing some inputs is scored only on what's available — weights renormalize over present features; nothing missing is ever treated as 0 (§55). Weights are centralized and documented in that one file, never buried in logic.

Tiers are gap-based (largest natural break in FantaScore within a role), not fixed-size buckets — see `app/scoring/tiers.py`.

### Auction methodology (§14-22)

- **ModelAuctionValue**: local market-average (from `auction_transactions`) if available, else an FVM-normalized-to-this-league's-budget heuristic; multiplied by a tier premium (replacement level, §17) and a scarcity multiplier (§18). Every component is returned so the UI can show *why* (§27). This is a documented v1 heuristic, not ground truth — it will get less approximate as local auction history accumulates.
- **RecommendedPrice bands** (Bargain/Fair/Aggressive/Maximum) are derived from ModelAuctionValue.
- **The hard invariant** (§21/§60): `MaximumBid = budget_remaining − (every OTHER remaining slot × base_price)`. Every band in `RecommendedPrice`, not just "Maximum", is clamped to this cap — see `app/auction/recommender.py`. This is enforced twice: once as the number shown in the UI, and again server-side in `record_transaction()` when a sale is actually logged, so it can't be bypassed by typing a higher number.
- **AuctionSimulator** (§23): Monte Carlo over a target shortlist's price uncertainty. It does **not** model 9 independent opponents bidding — that needs local transaction history this app hasn't accumulated yet, and is a natural MVP2/3 extension.

## Scope (MVP1)

Built: auth (single admin), league settings (configurable, not hardcoded), player database, manual/demo data import, FantaScore, tiers, ModelAuctionValue, RecommendedPrice, MaximumBid with the budget-completion invariant, live auction dashboard, roster/opponent tracking, auction simulator.

Deferred to MVP2: formation optimizer, StartabilityScore, injuries, probable lineups, news, alerts, multi-user league accounts, real API-Football/Fantacalcio.it/Understat data feeds.

Deferred to MVP3: trade engine, squad analytics, backtesting, model training, natural-language assistant.

## Setup

### Quick start: local single-user mode (no Docker/Postgres/Redis)

For running FantaMazor for yourself on one machine, the simplest path skips Postgres and Redis entirely: `DATABASE_URL=sqlite:///./fantamazor.db` creates its schema automatically on first startup (no Alembic needed), and if Redis isn't reachable the app transparently falls back to an in-memory cache (`app/core/cache.py`). This is what `backend/.env` is set to by default in this repo.

Once the backend venv (`backend/.venv`) and frontend deps (`frontend/node_modules`) are installed once (see below), everyday startup is just:

```bash
avvia-fantamazor.bat
```

at the repo root — it opens the backend and frontend each in their own window and opens http://localhost:3000 in your browser. Closing those two windows stops the app; running the script again starts it fresh, no reinstalling anything.

### Backend

Requires Python 3.11+. For the full setup with real Postgres + Redis (recommended once you're running a real league with other people, not just solo):

```bash
docker compose up -d          # postgres + redis
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
copy .env.example .env        # then edit DATABASE_URL/ADMIN_PASSWORD/SESSION_SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

For local single-user mode instead, skip `docker compose` and `alembic upgrade head` — just set `DATABASE_URL=sqlite:///./fantamazor.db` in `backend/.env` and start uvicorn; the schema is created for you.

On first startup the app seeds: the single admin user (from `ADMIN_USERNAME`/`ADMIN_PASSWORD`), the target league's default `LeagueSettings` (10 participants, 500 FM, 3/8/8/6 — see §1), its 10 `LeagueMembers`, and the known data-source rows.

Run the test suite (pure-function tests, no live DB needed — see `backend/app/tests/`):

```bash
cd backend
pytest
```

### Frontend

Requires Node 18+.

```bash
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

Open http://localhost:3000, log in with the admin credentials from `backend/.env`.

### Getting data in without any API keys

1. Go to **Impostazioni → Dati** (`/settings/data`).
2. Either click **"Usa dati demo"** (a small, clearly-fictional seed set — see `DEMO_DATA = True` in `app/providers/demo_data.py`), or upload a real listone as CSV (`name,role` required; `team,quotation,fvm` optional) or JSON.
3. Click **"Calcola FantaScore"**.
4. Go to **Asta → Setup**, create a session, then **Asta → Live** to run the auction.

## Required API keys

None are required for MVP1 (demo/manual mode). To enable live data later:

| Variable | Where | Purpose |
|---|---|---|
| `API_FOOTBALL_API_KEY`, `API_FOOTBALL_BASE_URL` | `backend/.env` | Structured player/team/fixture data (§4). Until set, `ApiFootballProvider` reports itself unavailable and the app runs entirely on demo/manual data. |

## Data requiring manual import

- Listone / quotations / FVM (`fantasy_quotes`) — no licensed Fantacalcio.it API is assumed available; import CSV/JSON via `/settings/data`.
- Historical per-season player stats (`player_season_stats`) — optional; if absent, FantaScore falls back to whatever inputs (typically just FVM) are present, per §55.

## Source freshness status

`GET /api/data/status` (and the `/settings/data` page) shows, per source: last successful sync, last failure, last error. Nothing is ever labeled "live" or "real-time" unless it actually is (§37/§57) — MVP1's demo/manual sources are explicitly marked as such in the UI.

## Testing

`backend/app/tests/` — pure-function tests (no live Postgres/Redis required to run them):

- `test_budget_constraints.py` — **the mandatory §60 invariant**: given 500 credits / 25 slots / 3-8-8-6, the engine never suggests a bid that makes completing the roster impossible. Includes a full 25-pick simulated auction always bidding the maximum allowed, proving the roster completes exactly on budget.
- `test_auction_engine.py` — scarcity, tier premium, ModelAuctionValue, simulator determinism/validation.
- `test_scoring.py` — FantaScore null-handling/renormalization, weight centralization, gap-based tiering.
- `test_providers.py` — manual-import validation, demo-data flagging, API-Football's unavailable-without-key behavior.

DB-integration tests (exercising `app/auction/live_engine.py` against a real database) are a natural next step once CI has Postgres available — the module is written against SQLAlchemy's ORM and is portable to SQLite for that purpose today (see `PortableJSON` in `app/db/models.py`).
