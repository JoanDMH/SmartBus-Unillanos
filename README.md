# SmartBus Unillanos — MVP

A data collection and analysis system for bus occupancy at Universidad de los Llanos (Villavicencio, Meta, Colombia).

---

## Prerequisites

Make sure the following tools are installed before starting:

| Tool | Minimum version | Verify installation |
|---|---|---|
| **Docker** | 24.0 | `docker --version` |
| **Docker Compose** | 2.20 | `docker compose version` |
| **.NET SDK** (optional, for local dev) | 10.0 | `dotnet --version` |
| **Python** (optional, for local dev) | 3.11 | `python --version` |
| **Node.js** (optional, for local dev) | 18.0 | `node --version` |

---

## Project structure

```
SmartBus-Unillanos/
├── mini-identity-api-dotnet/   ← Authentication API (.NET 10)
├── trip-log-service/           ← Trip logging microservice (Python · FastAPI · PostgreSQL)
│   ├── storage/database.py     ← PostgreSQL async layer (SQLAlchemy + asyncpg)
│   ├── services/ai_analysis.py ← AI demand analysis (Groq API)
│   └── ...
├── frontend/                   ← Web application (React + Vite → Nginx)
│   ├── nginx.conf              ← Reverse proxy config
│   └── ...
├── docker-compose.yml          ← Full environment orchestration
├── Dockerfile.auth             ← MiniIdentity container build
├── 01_project_context.md       ← Full project context
└── README.md                   ← This file
```

---

## Running with Docker (recommended)

### 1. Set up environment

Create a `.env` file in the project root:

```env
GROQ_API_KEY=gsk_YOUR_GROQ_API_KEY_HERE
```

### 2. Start all services

```powershell
docker compose up --build
```

This starts four containers:
- **PostgreSQL** on port `5432`
- **MiniIdentity Auth API** on port `5000`
- **trip-log-service** on port `8000`
- **Frontend (Nginx)** on port `80`

Wait for all services to report healthy status.

### 3. Register a user (required once per database reset)

```powershell
$body = '{"username":"testuser","email":"test@unillanos.edu.co","password":"Test123!"}'
Invoke-RestMethod -Uri "http://localhost:5000/api/auth/register" -Method Post -ContentType "application/json" -Body $body
```

### 4. Access the application

Open your browser at **http://localhost**

---

## Running locally (development)

Three terminals are required, one for each service. Start them in the order shown below.

### Terminal 0 — PostgreSQL (Docker)

```powershell
docker run -d --name smartbus-db -e POSTGRES_USER=smartbus -e POSTGRES_PASSWORD=smartbus123 -e POSTGRES_DB=smartbus -p 5432:5432 postgres:15-alpine
```

### Terminal 1 — Authentication API (port 5000)

```powershell
cd mini-identity-api-dotnet\src\MiniIdentityApi.Api
dotnet run --urls "http://localhost:5000"
```

### Terminal 2 — Trip log microservice (port 8000)

First time (create virtual environment and install dependencies):
```powershell
cd trip-log-service
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Subsequent runs:
```powershell
cd trip-log-service
.\venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

### Terminal 3 — Frontend (port 5173)

First time (install dependencies):
```powershell
cd frontend
npm install
```

Subsequent runs:
```powershell
cd frontend
npm run dev
```

Open **http://localhost:5173**

---

## Using the application

1. Open your browser at **http://localhost** (Docker) or **http://localhost:5173** (dev)
2. Log in with the registered credentials:
   - **Username:** `testuser`
   - **Password:** `Test123!`
3. The **Dashboard** shows operational statistics and the available bus route
4. Click **Registrar Viaje** to register a trip with occupancy data and ML context variables
5. Click **Historial** to view all registered trips
6. Use **Descargar CSV** to export trip data
7. Click **Generar análisis de demanda** for AI-powered demand insights

---

## AI Demand Analysis

The system includes an AI-powered demand analysis feature:

- **Endpoint:** `GET /trips/ai/demand-analysis` (protected)
- **Provider:** Groq Cloud (llama-3.1-8b-instant model)
- **Function:** Analyzes recorded trip data and generates Spanish-language recommendations about demand patterns, peak hours, and frequency optimization
- **Frontend:** Available in the Dashboard under "Análisis Inteligente"

Requires `GROQ_API_KEY` environment variable.

---

## Ports and services

| Service | Port | Technology | API documentation |
|---|---|---|---|
| PostgreSQL | `5432` | PostgreSQL 15 | — |
| MiniIdentity API | `5000` | .NET 10 / ASP.NET Core | `http://localhost:5000/swagger` |
| trip-log-service | `8000` | Python / FastAPI | `http://localhost:8000/docs` |
| Frontend | `80` (Docker) / `5173` (dev) | React / Vite / Nginx | — |

---

## Environment variables (trip-log-service)

The file `trip-log-service/.env` must contain:

```env
JWT_SECRET=THIS_IS_A_DEMO_KEY_CHANGE_IT_123456789
JWT_ISSUER=MiniIdentityApi
JWT_AUDIENCE=MiniIdentityApiUsers
PORT=8000
DATABASE_URL=postgresql+asyncpg://smartbus:smartbus123@localhost:5432/smartbus
GROQ_API_KEY=gsk_YOUR_GROQ_API_KEY_HERE
```

These values must match the JWT configuration in MiniIdentity's `appsettings.json`.

---

## Important notes

- **Persistent storage:** Trip data is stored in PostgreSQL and survives container restarts. The `postgres_data` Docker volume ensures data persistence.
- **Startup order:** Docker Compose handles service ordering automatically. For local dev: start PostgreSQL first, then MiniIdentity, trip-log-service, and finally the frontend.
- **CORS:** In Docker, Nginx acts as a reverse proxy, serving all services from the same origin (no CORS issues). In dev mode, Vite's proxy handles this.
- **Shared JWT secret:** Backend services validate JWT tokens independently using the same shared secret key.
- **JWT claims:** MiniIdentity puts the user UUID in the `sub` claim and the username in `unique_name`. The trip-log-service reads `unique_name` for the `registered_by` field.
- **MiniIdentity in-memory:** MiniIdentity still uses in-memory storage for users. Register a user each time the auth container restarts.
