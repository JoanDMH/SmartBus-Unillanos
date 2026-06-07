# SmartBus Unillanos — MVP Progress Tracker

> Last updated: 2026-06-07 (Milestone 3 — en progreso)

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
| `pages/LoginPage.jsx` | ✅ Done | SVG bus icon, gradient styling, link → /register |
| `pages/DashboardPage.jsx` | ✅ Done | SVG icons, welcome bar, stat cards, route card animated gradient |
| `pages/RegisterTripPage.jsx` | ✅ Done | Full form with ML variables: weather selector, academic week (1-18), special event checkbox |
| `pages/TripHistoryPage.jsx` | ✅ Done | Table with 8 columns including weather badge, academic week, special event |
| `App.jsx` | ✅ Done | BrowserRouter + PrivateRoute + all routes |
| `main.jsx` | ✅ Done | React root render |
| `index.css` | ✅ Done | Premium dark-mode design with form sections, custom checkbox, weather badges |
| `index.html` | ✅ Done | SEO meta tags |
| `package.json` | ✅ Done | react, react-dom, react-router-dom |
| `vite.config.js` | ✅ Done | Vite + React plugin + proxy /api → localhost:5000 (CORS fix) |

### Bugs fixed during Milestone 1

1. **CORS on MiniIdentity**: Fixed by adding Vite proxy (`/api → localhost:5000`).
2. **accessToken vs token**: MiniIdentity returns `{ accessToken }` not `{ token }`. Normalized in `authApi.js`.
3. **JWT sub claim**: MiniIdentity puts UUID in `sub` and username in `unique_name`. Updated `AuthContext.jsx` and `jwt_validator.py`.

### ML variables added (Milestone 1 — Iteration 2)

- Added Weather enum (SOLEADO, NUBLADO, LLUVIOSO) to TripCreate/TripResponse.
- Added academic_week (1-18) field.
- Added special_event boolean field.
- Updated RegisterTripPage with visual form sections.
- Updated TripHistoryPage table with 3 new columns + colored weather badges.

---

## Milestone 2 — Second Deliverable (completed)

### Requirement 0 — Database Migration (PostgreSQL)

| Item | Status | Notes |
|---|---|---|
| `storage/database.py` | ✅ Done | SQLAlchemy 2.0 async ORM + asyncpg driver |
| `TripRow` ORM model | ✅ Done | Maps to `trips` table, `DateTime(timezone=True)` |
| `init_db()` | ✅ Done | Auto-creates tables on startup |
| `get_session()` | ✅ Done | FastAPI dependency yielding `AsyncSession` |
| CRUD functions | ✅ Done | `save_trip`, `get_all_trips`, `get_trip_by_id`, `compute_stats` |

### Requirement 1 — Containerization (Docker)

| Container | Image | Port | Status |
|---|---|---|---|
| `postgres` | postgres:15-alpine | 5432 | ✅ Running (healthy) |
| `auth` | smartbus-unillanos-auth | 5000 | ✅ Running |
| `trip-log` | smartbus-unillanos-trip-log | 8000 | ✅ Running |
| `frontend` | smartbus-unillanos-frontend | 80 | ✅ Running |

**All 4 containers build and start successfully with `docker compose up --build`.**

### Requirement 3 — AI Integration (Groq)

| Item | Status | Notes |
|---|---|---|
| `services/ai_analysis.py` | ✅ Done | Groq API (llama-3.1-8b-instant), max 400 tokens, 30 recent trips |
| `GET /trips/ai/demand-analysis` | ✅ Done | Protected endpoint, returns `{ analysis: string }` |

### Azure Deployment (completed outside tracker)

| Recurso | Estado | URL |
|---|---|---|
| PostgreSQL Flexible Server | ✅ Running | `smartbus-db-server-joandmh.postgres.database.azure.com` |
| Container App — auth | ✅ Running | `smartbus-auth.nicepebble-7ac167f5.centralus.azurecontainerapps.io` |
| Container App — trip-log | ✅ Running | `smartbus-trips.nicepebble-7ac167f5.centralus.azurecontainerapps.io` |
| Static Web App — frontend | ✅ CI/CD activo | `nice-beach-041d9aa0f.7.azurestaticapps.net` |

### Bugs fixed during Milestone 2

1. **npm ci fails in Docker**: Lock file out of sync. Fixed with `npm install`.
2. **dotnet restore fails for solution file**: Fixed by restoring `.csproj` directly.
3. **asyncpg timezone error**: Fixed with `DateTime(timezone=True)` in ORM.
4. **Stray `y` on TripHistoryPage.jsx line 88**: Removed.

---

## Milestone 3 — ML Pipeline + Registro de Usuarios (en progreso)

> Sesión: 2026-06-07

### DEV-D3 — Registro de Usuarios (✅ Completado)

| File | Status | Notes |
|---|---|---|
| `frontend/src/pages/RegisterPage.jsx` | ✅ Done | Formulario con checklist de fortaleza de contraseña en tiempo real, feedback visual por regla (mayúscula, número, carácter especial, longitud). Nota de asignación de rol por administrador. Redirige al login tras éxito. |
| `frontend/src/api/authApi.js` | ✅ Updated | Añadida función `registerUser(username, email, password)` → `POST /api/auth/register` |
| `frontend/src/App.jsx` | ✅ Updated | Ruta pública `/register` añadida |
| `frontend/src/pages/LoginPage.jsx` | ✅ Updated | Link "Crear cuenta" → `/register` |

### DEV-A3 — Clima Automático (✅ Completado)

| File | Status | Notes |
|---|---|---|
| `trip-log-service/services/weather_client.py` | ✅ Done | Cliente async OpenWeatherMap (httpx). Mapeo: 2xx-6xx→LLUVIOSO, 7xx→NUBLADO, 800→SOLEADO, 80x→NUBLADO. Degradación elegante si no hay API key. |
| `trip-log-service/models/trip.py` | ✅ Updated | `weather` ahora `Optional[Weather] = None` — `None` activa auto-fetch |
| `trip-log-service/routers/trips_router.py` | ✅ Updated | Si `body.weather is None`, llama `get_current_weather()` antes de persistir |
| `trip-log-service/config.py` | ✅ Updated | Añadidas vars: `OPENWEATHER_API_KEY`, `OPENWEATHER_CITY`, `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_MODEL_CONTAINER`, `MODEL_LOCAL_CACHE_PATH` |

### DEV-B1 — Prophet (✅ Completado)

| File | Status | Notes |
|---|---|---|
| `ai-engine/train_prophet.py` | ✅ Done | Prophet con regresores exógenos (academic_week, special_event, weather_lluvioso, is_peak). Estacionalidad diaria + semanal multiplicativa. CV temporal con `initial` calculado sobre rango real de fechas (bug corregido). Logueo MLflow. Sube artefacto a Azure Blob. |

**Bug crítico corregido:** El cálculo de `initial` para la validación cruzada usaba `len(df)//3` (número de registros) en lugar del rango real de fechas en días, causando un crash cuando hay múltiples viajes por día.

### DEV-B2 — XGBoost (✅ Completado)

| File | Status | Notes |
|---|---|---|
| `ai-engine/train_xgboost.py` | ✅ Done | XGBoost con features tabulares: lag_1h, lag_24h, lag_168h, rolling_mean_24h. TimeSeriesSplit 5-fold. Feature importance logueado en MLflow. Regularización L1/L2 ajustada para datasets pequeños. |

**Bug crítico corregido (data leakage):** `df["y"].rolling(24).mean()` incluía `y[t]` en el cálculo de la media para predecir `y[t]`. Corregido con `df["y"].shift(1).rolling(24, min_periods=1).mean()` — la ventana ahora solo usa `y[t-24]…y[t-1]`.

### DEV-B3 — MLflow + Evaluación CI (✅ Completado)

| File | Status | Notes |
|---|---|---|
| `ai-engine/evaluate.py` | ✅ Done | Evalúa Prophet y/o XGBoost contra `holdout_dataset.csv`. Exit code 0 si MAE ≤ 5, exit code 1 si supera umbral (bloquea merge en CI). Loguea en MLflow. |
| `ai-engine/holdout_dataset.csv` | ✅ Done | 30 registros representativos de la Ruta Parque (picos mañana/mediodía/tarde, 3 condiciones climáticas, días lunes-viernes). |
| `ai-engine/db_loader.py` | ✅ Done | Carga trips de PostgreSQL (sync SQLAlchemy), añade features temporales e ingeniería de variables. |
| `ai-engine/upload.py` | ✅ Done | Sube artefactos `.pkl` a Azure Blob. Degradación elegante si no hay connection string. |
| `ai-engine/requirements.txt` | ✅ Done | prophet, xgboost, mlflow, scikit-learn, pandas, azure-storage-blob |
| `ai-engine/Dockerfile` | ✅ Done | Python 3.11-slim, job batch (no HTTP server) |
| `ai-engine/.env.example` | ✅ Done | DATABASE_URL, AZURE vars, MLFLOW_TRACKING_URI |

### DEV-B4 — Endpoint de Predicción (✅ Completado)

| File | Status | Notes |
|---|---|---|
| `trip-log-service/services/model_loader.py` | ✅ Done | Descarga modelos de Azure Blob en startup. Cache en memoria. Soporta `model_prophet.pkl` y `model_xgboost.pkl`. Degradación elegante. |
| `trip-log-service/routers/predict_router.py` | ✅ Done | `GET /trips/ai/predict-demand?date=&hour=&model=best`. Devuelve predicciones con intervalo de confianza. Soporta Prophet y XGBoost. |
| `trip-log-service/main.py` | ✅ Updated | v0.3.0. Registra `predict_router`. Llama `load_all_models()` en lifespan. |
| `trip-log-service/requirements.txt` | ✅ Updated | Añadidos: joblib, numpy, pandas, azure-storage-blob |

---

## Bugs Conocidos Corregidos (Milestone 3)

| # | Archivo | Bug | Corrección |
|---|---|---|---|
| 1 | `train_xgboost.py` | Data leakage: `rolling(24).mean()` incluía `y[t]` en el feature para predecir `y[t]` | `df["y"].shift(1).rolling(24, min_periods=1).mean()` |
| 2 | `train_prophet.py` | CV crash: `initial=f"{len(df)//3} days"` usaba conteo de filas como días | `initial_days = max(14, (ds.max()-ds.min()).days // 2)` |
| 3 | `predict_router.py` | Import sin usar: `import math`, `date as date_type` | Eliminados |

---

## Estructura Actual del Proyecto

```
SmartBus-Unillanos/
├── .env                          ← GROQ_API_KEY + OPENWEATHER_API_KEY (gitignored)
├── .gitignore                    ← Incluye azure_deployment_summary.md
├── docker-compose.yml
├── Dockerfile.auth
├── README.md
├── roadmap_desarrollo_pendiente.md
├── azure_deployment_summary.md   ← SOLO LOCAL — contiene credenciales Azure
│
├── documentation/                ← Reorganizado en Milestone 3
│   ├── memory.md                 ← Este archivo
│   ├── 01_project_context.md
│   ├── 02_mvp_specification.md
│   ├── azure_deployment_guide.md
│   ├── implementation_plan.md
│   ├── technical_guide_milestone2.md
│   └── walkthrough.md
│
├── ai-engine/                    ← NUEVO (Milestone 3)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example
│   ├── db_loader.py
│   ├── upload.py
│   ├── train_prophet.py          ← DEV-B1
│   ├── train_xgboost.py          ← DEV-B2
│   ├── evaluate.py               ← DEV-B3 / DEV-E1
│   └── holdout_dataset.csv       ← Dataset fijo de validación CI
│
├── mini-identity-api-dotnet/     ← Auth API (.NET 10, submodule)
│
├── trip-log-service/             ← FastAPI v0.3.0
│   ├── config.py                 ← + OPENWEATHER, AZURE_BLOB vars
│   ├── main.py                   ← v0.3.0, lifespan carga modelos ML
│   ├── models/trip.py            ← weather ahora Optional (auto-fetch)
│   ├── routers/trips_router.py   ← auto-fetch clima en POST /trips
│   ├── routers/predict_router.py ← NUEVO: GET /trips/ai/predict-demand
│   └── services/
│       ├── ai_analysis.py
│       ├── weather_client.py     ← NUEVO: cliente OpenWeatherMap
│       └── model_loader.py       ← NUEVO: carga .pkl desde Azure Blob
│
└── frontend/src/
    ├── App.jsx                   ← + ruta /register
    ├── api/authApi.js            ← + registerUser()
    └── pages/
        ├── LoginPage.jsx         ← + link "Crear cuenta"
        └── RegisterPage.jsx      ← NUEVO: formulario de registro
```

---

## API Endpoints (trip-log-service v0.3.0)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | Public | Health check |
| GET | `/routes` | Public | List available routes |
| POST | `/trips` | Bearer JWT | Register a new trip (weather auto-fetch si se omite) |
| GET | `/trips` | Bearer JWT | List trips (filtros: route_id, date) |
| GET | `/trips/stats/summary` | Bearer JWT | Occupancy statistics |
| GET | `/trips/ai/demand-analysis` | Bearer JWT | Análisis descriptivo Groq |
| GET | `/trips/ai/predict-demand` | Bearer JWT | **NUEVO** Predicción ML (Prophet/XGBoost) |
| GET | `/trips/{trip_id}` | Bearer JWT | Get single trip by ID |

---

## Variables de Entorno Requeridas (Milestone 3)

### trip-log-service/.env (añadidas)

```env
OPENWEATHER_API_KEY=<tu_key_gratuita_openweathermap>
OPENWEATHER_CITY=Villavicencio,CO
AZURE_STORAGE_CONNECTION_STRING=<connection_string_blob>
AZURE_MODEL_CONTAINER=smartbus-models
MODEL_LOCAL_CACHE_PATH=/tmp/smartbus_models
```

### ai-engine/.env

```env
DATABASE_URL=postgresql://smartbus:smartbus123@localhost:5432/smartbus
AZURE_STORAGE_CONNECTION_STRING=<connection_string_blob>
AZURE_MODEL_CONTAINER=smartbus-models
MLFLOW_TRACKING_URI=./mlruns
```

---

## Tareas Pendientes (Milestone 3)

- [ ] DEV-A1: APScheduler — limpieza nocturna de datos + GitHub Actions cron mensual
- [ ] DEV-A2: Evaluar disponibilidad TimescaleDB en Azure for Students; implementar índices compuestos como alternativa
- [ ] DEV-C1/C2/C3: optimization-service (PuLP) + endpoints weekly-schedule
- [ ] DEV-D1: PredictionDashboard (Recharts — demanda predicha vs. real)
- [ ] DEV-D2: ScheduleApprovalPage (human-in-the-loop)
- [ ] DEV-E1: GitHub Actions workflow de validación ML (evaluate.py en CI)
- [ ] DEV-E2: Detección de drift con APScheduler (Kolmogorov-Smirnov)
- [ ] DEV-E3: Workflow mensual de reentrenamiento automático
