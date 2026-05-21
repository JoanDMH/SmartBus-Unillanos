# SmartBus Unillanos — Milestone 2 Implementation Plan

This plan covers the four requirements from `technical_guide_milestone2.md`: database migration from in-memory to PostgreSQL, containerization with Docker, AI demand analysis endpoint (Groq), and frontend integration of the AI section.

> [!NOTE]
> Azure deployment (Requirement 2) is a **manual portal + infrastructure task** — I will prepare the codebase to be cloud-ready (environment variables, Dockerfiles, build args for URLs), but the actual Azure resource creation and deployment must be done by you in the Azure Portal after the code changes are complete.

---

## Proposed Changes

### 1. Database Migration — `trip-log-service` (Requirement 0)

The in-memory storage module is replaced with async PostgreSQL via SQLAlchemy 2.0 + asyncpg. Alembic is included for schema management.

#### [DELETE] [in_memory.py](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/trip-log-service/storage/in_memory.py)
Remove the in-memory storage module entirely.

#### [NEW] [database.py](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/trip-log-service/storage/database.py)
- SQLAlchemy async engine + session factory from `DATABASE_URL` env var
- `Trip` ORM model mapping to the `trips` table (UUID pk, route_id, bus_id, departure_time, passenger_count, weather, academic_week, special_event, notes, registered_by, created_at)
- Async functions: `init_db()`, `get_session()`, `save_trip()`, `get_all_trips()`, `get_trip_by_id()`, `compute_stats()`
- Auto-creates the table on startup (for development convenience; Alembic for production)

#### [MODIFY] [config.py](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/trip-log-service/config.py)
- Add `DATABASE_URL` and `GROQ_API_KEY` environment variable loading
- Default `DATABASE_URL` for local Docker Compose: `postgresql+asyncpg://smartbus:smartbus123@localhost:5432/smartbus`

#### [MODIFY] [main.py](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/trip-log-service/main.py)
- Add `lifespan` event handler to initialize the database (create tables) on startup
- Import from new `storage.database` module

#### [MODIFY] [trips_router.py](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/trip-log-service/routers/trips_router.py)
- Replace all `from storage.in_memory import ...` with `from storage.database import ...`
- Add `AsyncSession` dependency injection via `get_session`
- Convert all endpoint handlers to use async DB session
- Add new `GET /trips/ai/demand-analysis` endpoint (Requirement 3)

#### [MODIFY] [requirements.txt](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/trip-log-service/requirements.txt)
Add: `sqlalchemy>=2.0`, `asyncpg>=0.29`, `alembic>=1.13`, `httpx>=0.27`

#### [MODIFY] [.env](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/trip-log-service/.env)
Add: `DATABASE_URL` and `GROQ_API_KEY` variables

---

### 2. Containerization (Requirement 1)

#### [NEW] [Dockerfile](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/trip-log-service/Dockerfile)
Python 3.11-slim based, installs requirements, runs uvicorn on port 8000.

#### [NEW] [.dockerignore](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/trip-log-service/.dockerignore)
Exclude `venv/`, `__pycache__/`, `.env`.

#### [NEW] [Dockerfile](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/mini-identity-api-dotnet/Dockerfile)
.NET 10 multi-stage build: SDK for restore+publish, runtime for execution. Exposes port 5000.

#### [NEW] [.dockerignore](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/mini-identity-api-dotnet/.dockerignore)
Exclude `bin/`, `obj/`, `.vs/`.

#### [NEW] [Dockerfile](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/frontend/Dockerfile)
Multi-stage: Node 20-alpine for build, Nginx for serving. Accepts `VITE_AUTH_BASE_URL` and `VITE_TRIP_LOG_BASE_URL` as build args.

#### [NEW] [nginx.conf](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/frontend/nginx.conf)
SPA routing configuration for Nginx (try_files to index.html).

#### [NEW] [.dockerignore](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/frontend/.dockerignore)
Exclude `node_modules/`, `dist/`.

#### [MODIFY] [vite.config.js](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/frontend/vite.config.js)
No changes needed — the proxy config is only used in dev mode.

#### [MODIFY] [authApi.js](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/frontend/src/api/authApi.js)
Use `import.meta.env.VITE_AUTH_BASE_URL || '/api'` so production builds point to Azure URLs.

#### [MODIFY] [tripApi.js](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/frontend/src/api/tripApi.js)
Use `import.meta.env.VITE_TRIP_LOG_BASE_URL || ''` so production builds point to Azure URLs.
Add `getDemandAnalysis(token)` function for the AI endpoint.

#### [NEW] [docker-compose.yml](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/docker-compose.yml)
Four services: `postgres` (15-alpine, healthcheck, volume), `auth` (.NET), `trip-log` (FastAPI, depends_on postgres), `frontend` (Nginx). Persistent `postgres_data` volume.

#### [NEW] [.env](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/.env)
Root-level `.env` for `GROQ_API_KEY` used by docker-compose.

---

### 3. AI Integration (Requirement 3)

#### [NEW] [ai_analysis.py](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/trip-log-service/services/ai_analysis.py)
- `analyze_demand(trips: list) -> str` — builds structured prompt from trip data, calls Groq API (llama3-8b-8192), returns Spanish-language analysis with recommendations
- System prompt: university transport analyst, max 5 sentences, Spanish

#### [MODIFY] [trips_router.py](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/trip-log-service/routers/trips_router.py)
- Add `GET /trips/ai/demand-analysis` endpoint (protected, reads from PostgreSQL, returns AI analysis text)

#### [MODIFY] [DashboardPage.jsx](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/frontend/src/pages/DashboardPage.jsx)
- Add "Análisis Inteligente" section below the stats grid
- Button to trigger AI analysis, loading state, display response in a styled card with a sparkle/AI icon

---

### 4. Frontend Adjustments

#### [MODIFY] [index.css](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/frontend/src/index.css)
- Add styles for the AI analysis card (`.ai-card`, `.ai-card-text`, loading states)

#### [MODIFY] [TripHistoryPage.jsx](file:///c:/Users/Admin/OneDrive/Escritorio/SmartBus-Unillanos/frontend/src/pages/TripHistoryPage.jsx)
- Fix the stray `y` on line 88 (existing syntax error)

---

## User Review Required

> [!IMPORTANT]
> The Groq API key `gsk_YOUR_GROQ_API_KEY_HERE` from your technical guide will be placed in the `.env` files (which are gitignored). Please confirm this is acceptable. It will **never** be committed to source code.

> [!WARNING]
> The `mini-identity-api-dotnet` is a **git submodule** (per `.gitmodules`). The Dockerfile I create for it will be placed inside the submodule directory. If you want to keep the submodule clean, I can alternatively place the Dockerfile at the root level and adjust the docker-compose build context. Let me know your preference.

## Open Questions

1. **MiniIdentity CORS in Docker**: When running under docker-compose, the frontend (Nginx on port 80) will call `auth` and `trip-log` as separate containers. The Vite proxy won't exist in production. Should I configure Nginx to reverse-proxy `/api` to the auth container and `/routes`, `/trips` to the trip-log container? **This is the recommended approach** — it avoids CORS entirely and keeps the same URL patterns.

2. **`.gitignore` update**: Should I update the root `.gitignore` to include `*.env`, `__pycache__/`, `venv/`, `node_modules/`, `.env` etc.?

---

## Verification Plan

### Automated Tests
1. `docker-compose up --build` — all 4 containers start without errors
2. Register a user via `POST http://localhost:5000/api/auth/register`
3. Login via the frontend at `http://localhost:80`
4. Create a trip → verify it persists in PostgreSQL
5. Restart containers → verify trip data survives
6. Hit `GET /trips/ai/demand-analysis` → verify Groq response
7. Verify AI analysis section renders in the dashboard

### Manual Verification
- Full E2E flow through the browser
- Docker logs for each container
- Azure deployment (post-implementation, by the student)
