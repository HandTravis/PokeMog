# PokéRanker Changelog

All notable changes to this project are documented here, ordered chronologically by development phase.

---

## Phase 18 — UI Polish

### Added
- Page title changed from `frontend` to `PokéRanker` in `index.html`
- Favicon updated from `.svg` to `.png` via `public/favicon.png`

---

## Phase 17 — Shiny Sprite Toggle

### Added
- Shiny toggle button on `MatchupScreen` — switches both Pokémon cards to shiny sprites
- Shiny toggle button on `ResultsScreen` — switches all winner cards to shiny sprites
- `shiny` prop passed through to `PokemonCard` and `WinnerCard` components
- Sprite src falls back to standard sprite if `sprite_shiny_url` is null

---

## Phase 16 — User Authentication & Session History

### Backend
- `auth.py` — password hashing via `passlib`/`sha256_crypt`, JWT creation and validation via `PyJWT`, `get_current_user` and `get_optional_user` FastAPI dependencies
- `auth_routes.py` — `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- `GET /api/sessions/history` — returns all sessions for the authenticated user, ordered newest first, including filters and created_at
- `POST /api/sessions` updated to accept optional `user_id` from `get_optional_user` — guests can still create sessions
- `SessionOut` updated with `created_at` and `filters` fields
- `create_session` in `tournament.py` updated to accept and store `user_id`
- `/sessions/history` route placed before `/sessions/{session_id}` to prevent UUID route capturing the literal path segment
- `SECRET_KEY` and `ACCESS_TOKEN_EXPIRE_MINUTES` env vars added to backend
- `python-jose` replaced with `PyJWT` to fix `Illegal instruction` crash on ARM64/x86 architecture mismatch
- `passlib[bcrypt]` switched to `sha256_crypt` scheme for same architecture reason
- `email-validator` added to requirements for Pydantic `EmailStr`
- `auth_router` mounted at `/api` prefix in `main.py` alongside existing router

### Frontend
- `api.js` — in-memory token management (`setToken`, `getToken`, `clearToken`, `isAuthenticated`), Bearer token attached to all requests, `register`, `login`, `getMe`, `getUserSessions` added, `requestForm` helper for OAuth2 form-encoded login
- `AuthScreens.jsx` — shared `AuthForm` layout, `LoginScreen` and `RegisterScreen` with email/password fields, validation, error display, and "Continue as guest" option
- `SessionHistoryScreen.jsx` — session cards with status badge, date, pool size, target, filter tags, expandable results panel, Resume button for active sessions
- `App.jsx` — full screen routing updated with `LOGIN`, `REGISTER`, `HISTORY` screens, auth state (`user`), logout handler, nav bar shows email + logout when authenticated and Login link when guest

### Fixed
- `[object Object]` error in session history — added string type check before rendering error
- `created_at` showing as December 31 1969 — field was null in response, added it to `session_history` endpoint
- `python-jose` `Illegal instruction` crash — replaced with `PyJWT`
- Alembic initial migration failing on DO cluster — replaced `op.drop_index()` and `op.drop_constraint()` calls with `IF EXISTS` raw SQL and PostgreSQL anonymous `DO $$ ... $$` blocks

---

## Phase 15 — Alembic Migrations (`backend/migrations/`)

### Added
- Alembic initialized inside the backend container via `alembic init migrations`
- `migrations/env.py` updated to import `Base.metadata` from `app.models` for autogenerate support
- `DATABASE_URL` read from environment in `env.py`, replacing hardcoded connection string in `alembic.ini`
- `postgresql://` replaced with `postgresql+psycopg2://` for Alembic's sync driver
- `psycopg2-binary` added to `requirements.txt` as Alembic's sync dependency
- Initial migration generated via `alembic revision --autogenerate -m "initial schema"` capturing full current schema
- Second migration `add users table and user_id to sessions` generated after User model added
- `main.py` lifespan updated to no-op — migrations run via docker-compose `command` instead
- docker-compose backend command updated to `alembic upgrade head && uvicorn ...`
- `alembic upgrade head` added to `k8s/backend.yaml` command

### Decisions Made
- Alembic set up before user auth so the users table addition is handled as a proper versioned migration
- Sync `psycopg2` driver used for Alembic while keeping `asyncpg` for the FastAPI async runtime
- Migrations run at container startup rather than inside the FastAPI lifespan to avoid uvicorn reloader fork conflicts

---

## Phase 14 — DigitalOcean Cloud Deployment

### Added
- DigitalOcean account setup with $200 free credits
- `doctl` CLI installed and authenticated via API token
- DigitalOcean Container Registry (`pokeranker-registry`) created at basic tier
- 2-node Kubernetes cluster created in `nyc1` region with `s-2vcpu-4gb` nodes
- Images rebuilt for `linux/amd64` platform using `docker buildx` to fix ARM64/x86 architecture mismatch on Apple Silicon
- Images pushed to registry: `registry.digitalocean.com/pokeranker-registry/pokeranker-backend:latest` and `pokeranker-frontend:latest`
- Registry pull secret created manually in `pokeranker` namespace with correct `username: do` credentials
- `imagePullSecrets` added to `spec.template.spec` in both `backend.yaml` and `frontend.yaml`
- `imagePullPolicy` changed from `Never` to `Always` in both manifests
- Full registry image paths added to both manifests replacing local image names
- `PGDATA` env var set to `/var/lib/postgresql/data/pgdata` in `postgres.yaml` to fix DigitalOcean block storage mount point conflict
- Nginx ingress controller deployed to DO cluster
- Ingress `host:` rule removed to allow IP-based access without a custom domain
- Seeder run as one-off `kubectl run` pod with `imagePullSecrets` override against DO cluster DB
- App confirmed fully functional at `http://146.190.1.160`

### Fixed
- `ErrImageNeverPull` — changed `imagePullPolicy` from `Never` to `Always`
- `ErrImagePull` from Docker Hub — added full registry path to image names
- Registry secret in wrong namespace — used `sed` to replace `kube-system` with `pokeranker` in `doctl registry kubernetes-manifest` output
- `imagePullSecrets` in wrong location — moved from Deployment `spec` to `spec.template.spec`
- Platform mismatch (`no match for platform in manifest`) — rebuilt images with `--platform linux/amd64` using `docker buildx`
- Postgres init failure (`directory exists but is not empty`) — added `PGDATA` env var pointing to subdirectory
- 404 on raw IP access — removed `host: pokeranker.local` from ingress rule
- Empty database on first deploy — ran seeder as `kubectl run` one-off pod

---

## Phase 13 — Kubernetes (`k8s/`)

### Added
- `namespace.yaml` — isolated `pokeranker` namespace
- `secrets.yaml` — DB credentials via `stringData` (base64-encoded automatically by k8s)
- `postgres.yaml` — Deployment + ClusterIP Service + 2Gi PersistentVolumeClaim
- `backend.yaml` — Deployment + ClusterIP Service with `/health` liveness and readiness probes
- `frontend.yaml` — Deployment + ClusterIP Service with readiness/liveness probes
- `ingress.yaml` — Nginx ingress routing `/api` and `/health` to backend, `/` to frontend
- Seeder run as one-off `kubectl run` job against cluster DB

### Fixed
- Removed `rewrite-target: /` annotation that was stripping `/api` prefix before forwarding to FastAPI
- Switched to regex path matching with `use-regex: "true"` to preserve full path
- DB empty on first deploy: ran seeder as `kubectl run` one-off pod
- Double matchup generation caused by `_generate_round_matchups` being called twice — fixed with existence guard
- Wrong `round_id=1` keyword argument in `create_session` and `_advance_round` calls to `_generate_round_matchups` — corrected to pass `Round` object

---

## Phase 12 — GitHub Actions (`.github/workflows/ci.yml`)

### Added
- CI workflow triggering on push and pull requests to all branches
- Postgres 16 service container with healthcheck
- Python 3.12 setup with pip dependency caching
- `PYTHONPATH` and `DATABASE_URL` env vars for test runner
- `--tb=short -q` pytest flags for concise CI output

### Fixed
- Bumped `actions/checkout` to v5 and `actions/setup-python` to v6 to resolve Node.js 20 deprecation warnings

---

## Phase 11 — Test Suite (`backend/tests/`)

### Added
- `conftest.py` — SQLite in-memory test DB, per-test engine/session fixtures, 13-Pokémon seed fixture covering all filter cases
- `test_models.py` — ORM model tests: constraints, defaults, relationships, unique violations
- `test_tournament.py` — tournament logic tests: pool filtering, session creation, matchup generation, pick submission, target_remaining halting, round advancement
- `test_routes.py` — full API integration tests via async HTTP test client with dependency injection override
- `test_seed.py` — pure function tests for `get_generation` and `get_evolution_stage`
- `pyproject.toml` with `asyncio_mode = "auto"` for pytest-asyncio

### Fixed
- Async test support: added `pytest-asyncio`, `aiosqlite`, `anyio` to requirements
- `PYTHONPATH` env var added to tester service in docker-compose
- Removed `TestSeedPokemon` DB tests that conflicted with internal session management
- `test_combined_filters` assertion corrected (Moltres is fire + stage 1, pool = 2 not 1)
- `test_new_round_created_after_round_completes` updated to use `get_next_matchup` loop pattern and query round 2 directly

---

## Phase 10 — Frontend (`frontend/src/`)

### Added
- `api.js` — centralised API client using relative URLs for k8s compatibility
- `types.jsx` — type colour map and `TypeBadge` component for all 18 Pokémon types
- `SetupScreen.jsx` — filter picker (generation, type, evolution stage, legendary/mythical toggles) and target_remaining slider
- `MatchupScreen.jsx` — VS battle UI with Pokémon cards, sprites, type badges, progress bar, round indicator, and 900ms result animation
- `ResultsScreen.jsx` — winner grid with confetti animation and Rank Again button
- `App.jsx` — root component with global styles, Press Start 2P + DM Sans fonts, sticky nav bar, screen routing
- Production `Dockerfile.prod` using multi-stage build: Node builder → Nginx static server
- `nginx.conf` with SPA fallback routing

### Fixed
- Winners grid alignment for incomplete rows: switched from CSS Grid to Flexbox with `justifyContent: center`
- `VITE_API_URL` fallback changed from `"http://localhost:8000"` to `""` for relative URL support in k8s

---

## Phase 9 — API Routes (`backend/app/routes.py`)

### Added
- `GET /api/pokemon` — list Pokémon with optional query param filters
- `GET /api/pokemon/{id}` — single Pokémon lookup
- `POST /api/sessions` — create session with filters and target_remaining, returns pool size and message
- `GET /api/sessions/{id}` — session status including active count and current round
- `GET /api/sessions/{id}/next` — next undecided matchup with full Pokémon details
- `POST /api/sessions/{id}/matchups/{matchup_id}` — submit a pick
- `GET /api/sessions/{id}/results` — final survivors for completed session
- `DELETE /api/sessions/{id}` — abandon a session
- Pydantic v2 `model_config = ConfigDict(from_attributes=True)` replacing deprecated `class Config`

---

## Phase 8 — Tournament Logic (`backend/app/tournament.py`)

### Added
- `build_pool` — filters Pokémon by generation, type, evolution stage, legendary, mythical
- `create_session` — validates `target_remaining < pool_size`, creates session, filters, and session_pokemon rows
- `get_current_round` — returns most recent incomplete round
- `get_active_pokemon` — returns all non-eliminated Pokémon in a session
- `_generate_round_matchups` — pairs active Pokémon randomly, leaves odd one out as bye
- `get_next_matchup` — lazily returns next undecided matchup, advances round when complete
- `_check_tiebreaker` — creates extra matchup between bye Pokémon and a round winner when pool is odd
- `_advance_round` — eliminates losers, checks target_remaining, creates next round or completes session
- `submit_pick` — records winner, eliminates loser immediately, checks target_remaining after every pick
- `get_results` — returns all Pokémon with winner status for a completed session

### Fixed
- Shared session concurrent conflict in seed script
- Missing `await` on multiple `db.commit()` calls causing silent failures
- Session not found after creation: added explicit commits in `create_session`
- `_check_tiebreaker` crashing on empty `winner_ids` list when round just started
- Session not completing at `target_remaining`: moved elimination + completion check into `submit_pick`
- Double matchup generation: added guard in `_generate_round_matchups` checking for existing matchups
- Wrong argument passed to `_generate_round_matchups` in `create_session` and `_advance_round`

---

## Phase 7 — FastAPI App (`backend/app/main.py`)

### Added
- FastAPI app with lifespan context manager replacing deprecated `@app.on_event`
- `Base.metadata.create_all` on startup as safety net (later replaced by Alembic migrations)
- CORS middleware allowing `localhost:5173` for local dev
- Router mounted at `/api` prefix
- `/health` endpoint for liveness/readiness probes

---

## Phase 6 — Database Connection (`backend/app/database.py`)

### Added
- Async SQLAlchemy engine with `asyncpg` driver
- `AsyncSessionLocal` session factory
- `get_db` FastAPI dependency with automatic commit on success and rollback on exception
- `SQL_ECHO` env var support for query logging
- Correct `AsyncGenerator[AsyncSession, None]` return type annotation

---

## Phase 5 — SQLAlchemy Models (`backend/app/models.py`)

### Added
- Declarative base with all tables mirroring `schema.sql` exactly
- Python enums: `PokemonTypeEnum`, `SessionStatus`, `PokemonStatus`
- Full relationship wiring including three separate FK relationships on `Matchup` (pokemon_a, pokemon_b, winner)
- `native_enum=False` on all enum columns to avoid Postgres type cast issues with asyncpg
- `expire_on_commit=False` on session factory to keep ORM objects usable after commit

### Fixed
- `native_enum` argument placement moved inside `Enum()` constructor to resolve SAWarning

---

## Phase 4 — Seed Script (`backend/app/seed.py`)

### Added
- Async seed script using `httpx` and `asyncpg` to fetch from PokéAPI
- Generation ranges map for dex ID → generation lookup
- Evolution stage resolved by walking full evolution chain recursively
- Batched requests (20 at a time) to avoid rate limiting PokéAPI
- `ON CONFLICT DO NOTHING` for full idempotency — safe to re-run
- Each Pokémon gets its own session to support concurrent `asyncio.gather`
- `GENERATION_LIMIT` env var support (default 9, set to 1 for smoke testing)

### Fixed
- Concurrent session conflict: moved from shared session to per-Pokémon sessions
- Missing `await` on `db.commit()` causing silent no-ops

---

## Phase 3 — Docker Compose (`docker-compose.yml`)

### Added
- `db` service with Postgres 16 Alpine, healthcheck via `pg_isready`, named volume for persistence
- `backend` service with hot-reload via volume mount, depends on DB healthcheck
- `frontend` service with Vite dev server, node_modules isolated inside container
- `seeder` service under `seed` profile — runs on demand, never on `docker compose up`
- `tester` service under `test` profile for running pytest suite
- `GENERATION_LIMIT` env var on seeder to control how many generations to seed
- `SQL_ECHO` env var on backend for query logging in dev
- `SEED_ON_STARTUP` env var as optional alternative seeding trigger

---

## Phase 2 — Database Schema (`db/schema.sql`)

### Added
- `pokemon` table with national dex ID, generation, evolution stage, legendary/mythical flags, sprite URLs
- `pokemon_types` join table supporting dual typing with slot constraints
- `sessions` table tracking tournament runs with `target_remaining` and status
- `session_filters` table capturing filter selections per session for reproducibility
- `session_pokemon` table managing each Pokémon's status within a session
- `rounds` table with unique constraint on `(session_id, round_number)`
- `matchups` table with `winner_id` (NULL until decided) and CHECK constraint preventing same-Pokémon matchups
- Indexes on generation, evolution stage, legendary, mythical, type, and session/round foreign keys
- `uuid-ossp` extension for UUID primary keys

---

## Phase 1 — Project Architecture & Scaffolding

### Decisions Made
- Established 3-service architecture: React frontend, FastAPI backend, PostgreSQL database
- Chose monorepo structure with `frontend/`, `backend/`, `db/`, `k8s/` directories
- Selected data strategy: seed from PokéAPI once, then serve entirely from local DB
- Tournament logic placed entirely in backend; React acts as a pure display layer