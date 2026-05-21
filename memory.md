# SmartBus Unillanos — MVP Progress Tracker

> Last updated: 2026-05-21 (Milestone 2 — completed)

---

## Milestone 1 — MVP (completed)

### trip-log-service (original — in-memory)

| File | Status | Notes |
|---|---|---|
| `config.py` | ✅ Done | Loads JWT_SECRET, JWT_ISSUER, JWT_AUDIENCE from .env |
| `storage/in_memory.py` | ❌ Removed | Replaced by `storage/database.py` in Milestone 2 |
| `models/route.py` | ✅ Done | RouteInfo Pydantic model |
| `models/trip.py` | ✅ Done | TripCreate + TripResponse with ML variables: weather (enum), academic_week (1-18), special_event (bool) |
| `auth/jwt_validator.py` | ✅ Done | HTTPBearer + pyjwt decode with HS256. Uses `unique_name` claim for readable username |
| `routers/routes_router.py` | ✅ Done | GET /routes — public, returns hardcoded Ruta Parque |
| `routers/trips_router.py` | ✅ Done | POST /trips includes weather, academic_week, special_event fields |
| `main.py` | ✅ Done | FastAPI app + CORS (allow all origins) + routers included |
| `requirements.txt` | ✅ Done | fastapi, uvicorn, pyjwt, python-dotenv |
| `.env.example` / `.env` | ✅ Done | JWT configuration matches MiniIdentity appsettings |

### Frontend (Milestone 1)

| File | Status | Notes |
|---|---|---|
| `context/AuthContext.jsx` | ✅ Done | Uses `unique_name` JWT claim for username display |
| `api/authApi.js` | ✅ Done | Normalizes `accessToken` → `token` from MiniIdentity response |
| `api/tripApi.js` | ✅ Done | getRoutes, getTrips, createTrip, getTripStats |
| `pages/LoginPage.jsx` | ✅ Done | SVG bus icon (no emoji), gradient styling |
| `pages/DashboardPage.jsx` | ✅ Done | SVG icons throughout, welcome bar with avatar, stat cards with icons, route card with animated gradient border + "Activa" badge |
| `pages/RegisterTripPage.jsx` | ✅ Done | Full form with ML variables: weather selector, academic week selector (1-18 with labels), special event checkbox |
| `pages/TripHistoryPage.jsx` | ✅ Done | Table with 8 columns including weather badge, academic week, special event |
| `App.jsx` | ✅ Done | BrowserRouter + PrivateRoute + all 4 routes |
| `main.jsx` | ✅ Done | React root render |
| `index.css` | ✅ Done | Premium dark-mode design with form sections, custom checkbox, weather badges |
| `index.html` | ✅ Done | SEO meta tags |
| `package.json` | ✅ Done | react, react-dom, react-router-dom |
| `vite.config.js` | ✅ Done | Vite + React plugin + proxy /api → localhost:5000 (CORS fix) |

### Bugs fixed during Milestone 1

1. **CORS on MiniIdentity**: MiniIdentity doesn't have CORS enabled. Fixed by adding Vite proxy (`/api → localhost:5000`).
2. **accessToken vs token**: MiniIdentity returns `{ accessToken }` not `{ token }`. Normalized in `authApi.js`.
3. **JWT sub claim**: MiniIdentity puts UUID in `sub` and username in `unique_name`. Updated `AuthContext.jsx` and `jwt_validator.py` to use `unique_name`.

### ML variables added (Milestone 1 — Iteration 2)

- Added Weather enum (SOLEADO, NUBLADO, LLUVIOSO) to TripCreate/TripResponse.
- Added academic_week (1-18) field.
- Added special_event boolean field.
- Updated RegisterTripPage with visual form sections: "Datos del viaje" + "Variables de contexto".
- Updated TripHistoryPage table with 3 new columns + colored weather badges.

---

## Milestone 2 — Second Deliverable (completed)

### Requirement 0 — Database Migration (PostgreSQL)

| Item | Status | Notes |
|---|---|---|
| `storage/in_memory.py` | ❌ Deleted | Was the old RAM-based storage |
| `storage/database.py` | ✅ Created | SQLAlchemy 2.0 async ORM + asyncpg driver |
| `TripRow` ORM model | ✅ Done | Maps to `trips` table with all fields including ML variables |
| `DateTime(timezone=True)` | ✅ Fixed | Columns use tz-aware timestamps to avoid asyncpg offset error |
| `init_db()` | ✅ Done | Auto-creates tables on startup via `Base.metadata.create_all` |
| `get_session()` | ✅ Done | FastAPI dependency yielding `AsyncSession` |
| CRUD functions | ✅ Done | `save_trip`, `get_all_trips`, `get_trip_by_id`, `compute_stats` — all take `AsyncSession` as first param |
| `config.py` | ✅ Updated | Added `DATABASE_URL` + `GROQ_API_KEY` env vars |
| `requirements.txt` | ✅ Updated | Added `sqlalchemy>=2.0`, `asyncpg>=0.29`, `alembic>=1.13`, `httpx>=0.27` |
| `main.py` | ✅ Updated | Version 0.2.0, async `lifespan` handler calls `init_db()` on startup |
| `trips_router.py` | ✅ Rewritten | All endpoints use `AsyncSession` dependency injection. Weather enum `.value` stored as string |
| `.env` / `.env.example` | ✅ Updated | Added `DATABASE_URL` and `GROQ_API_KEY` |
| Local venv | ✅ Reinstalled | Python 3.14 venv with all new dependencies. VS Code must select `.\trip-log-service\venv\Scripts\python.exe` |

**Key design decision:** `DateTime(timezone=True)` columns → PostgreSQL `TIMESTAMP WITH TIME ZONE`. Required because the frontend sends ISO datetimes with timezone info, and asyncpg rejects mixing tz-aware and tz-naive datetimes.

### Requirement 1 — Containerization (Docker)

| Item | Status | Notes |
|---|---|---|
| `trip-log-service/Dockerfile` | ✅ Created | Python 3.11-slim, pip install, uvicorn on port 8000 |
| `trip-log-service/.dockerignore` | ✅ Created | Excludes `venv/`, `__pycache__/`, `.env` |
| `Dockerfile.auth` (project root) | ✅ Created | .NET 10 multi-stage build. Build context is project root. Restores API project directly (not solution file — avoids missing Tests project error) |
| `mini-identity-api-dotnet/.dockerignore` | ✅ Created | Excludes `bin/`, `obj/`, `.vs/` |
| `frontend/Dockerfile` | ✅ Created | Multi-stage: Node 20-alpine build → Nginx serve. Uses `npm install` (not `npm ci` — lock file sync issue). Accepts `VITE_AUTH_BASE_URL` + `VITE_TRIP_LOG_BASE_URL` build args |
| `frontend/nginx.conf` | ✅ Created | Reverse proxy: `/api/` → auth:5000, `/routes` + `/trips` → trip-log:8000. SPA fallback via `try_files`. Static asset caching |
| `frontend/.dockerignore` | ✅ Created | Excludes `node_modules/`, `dist/` |
| `docker-compose.yml` | ✅ Created | 4 services: `postgres` (15-alpine, healthcheck, `postgres_data` volume), `auth` (from Dockerfile.auth), `trip-log` (depends_on postgres healthy), `frontend` (Nginx on port 80) |
| `.env` (project root) | ✅ Created | `GROQ_API_KEY` for docker-compose interpolation |
| `.gitignore` | ✅ Updated | Comprehensive: `.env`, `__pycache__/`, `venv/`, `node_modules/`, `dist/`, `.vs/`, etc. Keeps `.env.example` |

**Build verification (Docker Compose):**

| Container | Image | Port | Status |
|---|---|---|---|
| `postgres` | postgres:15-alpine | 5432 | ✅ Running (healthy) |
| `auth` | smartbus-unillanos-auth | 5000 | ✅ Running |
| `trip-log` | smartbus-unillanos-trip-log | 8000 | ✅ Running |
| `frontend` | smartbus-unillanos-frontend | 80 | ✅ Running |

**All 4 containers build and start successfully with `docker compose up --build`.**

### Bugs fixed during Milestone 2

1. **npm ci fails in Docker**: Lock file out of sync between Node 20 (Docker) and local Node. Fixed by using `npm install` instead of `npm ci` in `frontend/Dockerfile`.
2. **dotnet restore fails for solution file**: `MiniIdentityApi.slnx` references a Tests project not copied to Docker. Fixed by restoring the API `.csproj` directly instead of the solution file.
3. **asyncpg timezone error**: `can't subtract offset-naive and offset-aware datetimes`. Fixed by using `DateTime(timezone=True)` in ORM columns so PostgreSQL uses `TIMESTAMP WITH TIME ZONE`.
4. **Stray `y` on TripHistoryPage.jsx line 88**: Syntax error causing frontend issues. Removed.

### Requirement 3 — AI Integration (Groq)

| Item | Status | Notes |
|---|---|---|
| `services/__init__.py` | ✅ Created | Package init |
| `services/ai_analysis.py` | ✅ Created | `analyze_demand(trips)` → calls Groq API (llama-3.1-8b-instant), system prompt in Spanish, max 400 tokens, payload optimized to 30 recent trips |
| `GET /trips/ai/demand-analysis` | ✅ Added | Protected endpoint in `trips_router.py`. Reads from PostgreSQL, slices to 30 most recent trips, returns `{ analysis: string }` |
| `GROQ_API_KEY` | ✅ Configured | In `.env` (local), `docker-compose.yml` (container), and `.env` (root for compose interpolation) |

**AI implementation details:**
- Provider: Groq Cloud (`https://api.groq.com/openai/v1/chat/completions`)
- Model: `llama-3.1-8b-instant` (upgraded due to `llama3-8b-8192` deprecation)
- Context constraint: Limit analysis to the 30 most recent trips to bypass `413 Payload Too Large` rate limits on free API keys
- System prompt: Spanish-language transport analysis assistant, max 5 sentences
- User prompt: structured trip data with route, bus, departure time, passengers, weather, academic week, special event
- Timeout: 30 seconds
- HTTP client: `httpx.AsyncClient`

### Requirement 4 — Frontend Changes (Milestone 2)

| Item | Status | Notes |
|---|---|---|
| `api/authApi.js` | ✅ Updated | Uses `import.meta.env.VITE_AUTH_BASE_URL \|\| '/api'` for production builds |
| `api/tripApi.js` | ✅ Updated | Uses `import.meta.env.VITE_TRIP_LOG_BASE_URL \|\| ''`. Added `getDemandAnalysis(token)` function |
| `pages/DashboardPage.jsx` | ✅ Updated | Added "Análisis Inteligente" section with: sparkle icon, "IA · GROQ" badge, description text, AI response card with gradient border-left, "Generar análisis de demanda" button with loading state |
| `index.css` | ✅ Updated | Added `.ai-card`, `.ai-card-badge`, `.ai-card-content`, `.ai-card-text`, `.btn-ai` (violet gradient), `.ai-icon` with sparkle-pulse animation |
| `pages/TripHistoryPage.jsx` | ✅ Fixed | Removed stray `y` character on line 88 |

### README.md — Updated

- Added Docker Compose instructions as recommended way to run
- Added PostgreSQL standalone container for local dev
- Added AI Demand Analysis documentation
- Updated ports table (port 80 for Docker frontend)
- Added environment variable documentation for `DATABASE_URL` and `GROQ_API_KEY`

---

## Current Project Structure

```
SmartBus-Unillanos/
├── .env                          ← GROQ_API_KEY for docker-compose (gitignored)
├── .gitignore                    ← Comprehensive ignore rules
├── docker-compose.yml            ← Orchestrates 4 services
├── Dockerfile.auth               ← MiniIdentity .NET multi-stage build
├── README.md                     ← Updated with Docker + AI docs
├── 01_project_context.md
├── technical_guide_milestone2.md
│
├── mini-identity-api-dotnet/     ← Auth API (.NET 10, submodule)
│   ├── .dockerignore
│   └── src/...
│
├── trip-log-service/             ← Trip logging microservice (Python · FastAPI)
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── .env / .env.example       ← JWT + DATABASE_URL + GROQ_API_KEY
│   ├── requirements.txt          ← fastapi, uvicorn, pyjwt, sqlalchemy, asyncpg, alembic, httpx
│   ├── config.py                 ← All env vars loaded here
│   ├── main.py                   ← v0.2.0, lifespan handler for DB init
│   ├── auth/jwt_validator.py
│   ├── models/route.py
│   ├── models/trip.py            ← Pydantic models (Weather enum, TripCreate, TripResponse)
│   ├── routers/routes_router.py
│   ├── routers/trips_router.py   ← CRUD + stats + AI analysis endpoint
│   ├── services/__init__.py
│   ├── services/ai_analysis.py   ← Groq API integration
│   ├── storage/__init__.py
│   └── storage/database.py       ← SQLAlchemy async ORM (TripRow model, CRUD functions)
│
└── frontend/                     ← Web application (React + Vite → Nginx)
    ├── Dockerfile                ← Multi-stage: Node build → Nginx serve
    ├── .dockerignore
    ├── nginx.conf                ← Reverse proxy + SPA routing
    ├── index.html
    ├── package.json              ← react 19, react-router-dom 7, vite 8
    ├── vite.config.js            ← Dev proxy: /api→:5000, /routes+/trips→:8000
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── index.css             ← Premium dark-mode + AI card styles
        ├── api/authApi.js        ← VITE_AUTH_BASE_URL env var support
        ├── api/tripApi.js        ← VITE_TRIP_LOG_BASE_URL + getDemandAnalysis()
        ├── context/AuthContext.jsx
        └── pages/
            ├── LoginPage.jsx
            ├── DashboardPage.jsx ← Stats + AI analysis section + routes
            ├── RegisterTripPage.jsx
            └── TripHistoryPage.jsx
```

---

## Ports & Services

| Service | Port (Docker) | Port (Local Dev) | Technology |
|---|---|---|---|
| PostgreSQL | 5432 | 5432 | PostgreSQL 15-alpine |
| MiniIdentity Auth API | 5000 | 5000 | .NET 10 / ASP.NET Core |
| trip-log-service | 8000 | 8000 | Python 3.11 / FastAPI |
| Frontend | 80 (Nginx) | 5173 (Vite) | React 19 / Vite 8 |

---

## API Endpoints (trip-log-service)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | Public | Health check |
| GET | `/routes` | Public | List available routes |
| POST | `/trips` | Bearer JWT | Register a new trip |
| GET | `/trips` | Bearer JWT | List trips (optional filters: route_id, date) |
| GET | `/trips/stats/summary` | Bearer JWT | Occupancy statistics |
| GET | `/trips/ai/demand-analysis` | Bearer JWT | AI-generated demand analysis (Groq) |
| GET | `/trips/{trip_id}` | Bearer JWT | Get single trip by ID |

---

## Environment Variables

### trip-log-service/.env

```env
JWT_SECRET=THIS_IS_A_DEMO_KEY_CHANGE_IT_123456789
JWT_ISSUER=MiniIdentityApi
JWT_AUDIENCE=MiniIdentityApiUsers
PORT=8000
DATABASE_URL=postgresql+asyncpg://smartbus:smartbus123@localhost:5432/smartbus
GROQ_API_KEY=gsk_...
```

### Docker Compose uses

- `DATABASE_URL=postgresql+asyncpg://smartbus:smartbus123@postgres:5432/smartbus` (internal Docker DNS)
- `GROQ_API_KEY=${GROQ_API_KEY}` (interpolated from root `.env`)

---

## Verification Status

| Step | Status |
|---|---|
| trip-log-service starts without errors | ✅ Verified |
| Swagger UI shows all 7 endpoints | ✅ Verified (added AI endpoint) |
| Frontend starts without errors | ✅ Verified |
| Login flow works end to end | ✅ Verified (via Docker Nginx) |
| Dashboard loads routes + stats | ✅ Verified |
| AI analysis section visible in dashboard | ✅ Verified |
| Register trip form submits successfully | ✅ Verified |
| Trip history table displays registered trips | ✅ Verified |
| Stats update after registering a trip | ✅ Verified |
| AI analysis generates Groq response | ✅ Verified (using llama-3.1-8b-instant and 30-trip payload limit) |
| Data persists across container restart | ✅ Verified (using postgres_data volume) |
| docker compose up --build (all 4 containers) | ✅ Verified |
| Logout clears token and redirects | ✅ Verified |

---

## Pending Tasks (Milestone 2)

- [x] E2E verification: register trips → verify persistence → test AI analysis
- [x] Update walkthrough.md with Milestone 2 changes
- [ ] Azure deployment (manual — Azure Portal)
  - [ ] Azure Database for PostgreSQL Flexible Server
  - [ ] Azure Container Apps (auth + trip-log)
  - [ ] Azure Static Web Apps (frontend)
