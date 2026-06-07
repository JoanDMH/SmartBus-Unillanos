# SmartBus Unillanos — Technical Guide: Second Milestone

## Context

This milestone builds on the MVP delivered in the first submission: a React frontend
connected to the MiniIdentity authentication API and to the `trip-log-service` FastAPI
microservice, which until now stored all data **in RAM**.

The goal of this milestone is threefold: **migrate persistence to a real database**,
**containerize** the solution with Docker, and **deploy it to the cloud** on Azure,
while also adding an artificial intelligence feature.

> **The principle driving this entire milestone:** data must survive a container restart.
> As long as `in_memory.py` remains the data source, no cloud deployment will be stable.
> Migrating to PostgreSQL is not optional — it is the prerequisite that makes everything
> else possible.

---

## Requirement 0 — Database migration (prerequisite)

Before dockerizing or deploying anything, `trip-log-service` must stop using
`in_memory.py` and connect to **PostgreSQL**.

This is a prerequisite because Azure Container Apps is serverless by nature: it scales
to zero when there is no traffic and restarts containers frequently. If persistence
remains in memory, **the entire trip history will be lost every time the container
restarts**, leaving the AI endpoint with no data to analyze.

### Changes to trip-log-service

**Remove:** `storage/in_memory.py`

**Add:** `storage/database.py` — PostgreSQL connection using `SQLAlchemy` with async
support.

**New dependencies in `requirements.txt`:**

```
sqlalchemy>=2.0
asyncpg>=0.29
alembic>=1.13
```

**New environment variable:**

```env
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/smartbus
```

**Required table:**

```sql
CREATE TABLE trips (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    route_id        VARCHAR(50)  NOT NULL,
    bus_id          VARCHAR(50)  NOT NULL,
    departure_time  TIMESTAMP    NOT NULL,
    passenger_count INTEGER      NOT NULL CHECK (passenger_count BETWEEN 0 AND 100),
    notes           TEXT,
    registered_by   VARCHAR(100) NOT NULL,
    created_at      TIMESTAMP    NOT NULL DEFAULT now()
);
```

**What changes in the routers:** every function that previously called `in_memory.py`
now executes SQL queries against this table. The endpoint interface (paths, request
bodies, responses) does not change — only the storage layer changes.

---

## Requirement 1 — Containerization

With persistence solved, each service gets its own `Dockerfile` and the complete
environment is described in a `docker-compose.yml`.

### Project services

| Service             | Technology             | Local port |
| ------------------- | ---------------------- | ---------- |
| `postgres`          | PostgreSQL 15          | 5432       |
| `mini-identity-api` | .NET 10 / ASP.NET Core | 5000       |
| `trip-log-service`  | Python 3.11 / FastAPI  | 8000       |
| `frontend`          | React + Vite → Nginx   | 80         |

### Minimum required

- A working `Dockerfile` for each team-owned service (`mini-identity-api`,
  `trip-log-service`, `frontend`).
- Each container must start correctly with `docker build` + `docker run`.
- No credentials or URLs hardcoded in source code — everything goes as environment
  variables.

### Full docker-compose.yml

```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: smartbus
      POSTGRES_PASSWORD: smartbus123
      POSTGRES_DB: smartbus
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U smartbus"]
      interval: 5s
      timeout: 5s
      retries: 5

  auth:
    build: ./mini-identity-api-dotnet
    ports:
      - "5000:5000"
    environment:
      - ASPNETCORE_URLS=http://+:5000

  trip-log:
    build: ./trip-log-service
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql+asyncpg://smartbus:smartbus123@postgres:5432/smartbus
      - JWT_SECRET=THIS_IS_A_DEMO_KEY_CHANGE_IT_123456789
      - JWT_ISSUER=MiniIdentityApi
      - JWT_AUDIENCE=MiniIdentityApiUsers
      - GROQ_API_KEY=${GROQ_API_KEY}


  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - auth
      - trip-log

volumes:
  postgres_data:
```

> The `postgres_data` volume ensures data persists even if the Postgres container
> restarts. Without it, the database would be wiped on every `docker-compose down`.

### Dockerfile — trip-log-service

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Dockerfile — frontend (multi-stage with Nginx)

The frontend must be built for production. It cannot be served with Vite's development
server in a real environment.

```dockerfile
# Stage 1 — build
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
ARG VITE_AUTH_BASE_URL
ARG VITE_TRIP_LOG_BASE_URL
RUN npm run build

# Stage 2 — serve
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```

Backend service URLs are injected as `ARG` values at build time so that Vite embeds
them into the resulting static bundle.

---

## Requirement 2 — Azure deployment

### Recommended deployment architecture

```
                    ┌─────────────────────────────────────────┐
                    │           Microsoft Azure               │
                    │                                         │
  User              │  ┌──────────────────────────────────┐   │
  (browser) ────────┼─►│     Azure Static Web Apps        │   │
                    │  │     (React frontend)              │   │
                    │  └──────────────┬───────────────────┘   │
                    │                 │ HTTP/REST              │
                    │  ┌──────────────▼───────────────────┐   │
                    │  │     Azure Container Apps          │   │
                    │  │                                   │   │
                    │  │  ┌─────────────┐ ┌─────────────┐ │   │
                    │  │  │    auth     │ │  trip-log   │ │   │
                    │  │  │  (.NET 10)  │ │  (FastAPI)  │ │   │
                    │  │  └─────────────┘ └──────┬──────┘ │   │
                    │  └─────────────────────────┼────────┘   │
                    │                             │            │
                    │  ┌──────────────────────────▼────────┐   │
                    │  │  Azure Database for PostgreSQL    │   │
                    │  │  Flexible Server (free tier)      │   │
                    │  └───────────────────────────────────┘   │
                    └─────────────────────────────────────────┘
```

### Azure services to use

| Component                   | Azure service                                 | Cost                                  |
| --------------------------- | --------------------------------------------- | ------------------------------------- |
| Frontend                    | Azure Static Web Apps                         | Free, no time limit                   |
| Auth API + trip-log-service | Azure Container Apps                          | Free up to 180,000 vCPU-seconds/month |
| Database                    | Azure Database for PostgreSQL Flexible Server | Free for 12 months (B1ms tier)        |

Note: An Azure account with student credits is available for use during the development of this project. However, to avoid charges, you should use Azure's free services.

### Why this combination

- **Azure Static Web Apps** is permanently free for static frontends. React compiled
  with Vite produces exactly that.
- **Azure Container Apps** manages Docker containers without requiring server
  administration. The free tier comfortably covers academic usage.
- **Azure Database for PostgreSQL Flexible Server** on the free tier provides a
  managed database with automatic backups. This is the correct alternative to running
  PostgreSQL inside a container in the cloud, which does not guarantee real persistence
  in a serverless environment.

### Deployment flow

```
1. docker build  →  verified local image
2. docker push   →  Docker Hub (free, public repository)
3. Azure portal  →  Create Azure Database for PostgreSQL Flexible Server
4. Azure portal  →  Container Apps: create app from Docker Hub image
5. Azure portal  →  Set environment variables (DATABASE_URL points to Azure PostgreSQL)
6. Azure portal  →  Static Web Apps: connect GitHub repo, automatic frontend deploy
7. Verify        →  Public URL accessible and demo functional without touching localhost
```

### DATABASE_URL in Azure

In Azure Container Apps, the `DATABASE_URL` environment variable for `trip-log-service`
must point to the Azure managed server, not to the local Postgres container:

```env
DATABASE_URL=postgresql+asyncpg://smartbus:password@server.postgres.database.azure.com:5432/smartbus
```

### Service URLs in production

The production frontend cannot use `localhost`. URLs are set at container build time:

```env
VITE_AUTH_BASE_URL=https://auth.gentleriver-abc123.eastus.azurecontainerapps.io
VITE_TRIP_LOG_BASE_URL=https://trip-log.gentleriver-abc123.eastus.azurecontainerapps.io
```

---

## Requirement 3 — AI integration

### Feature — Intelligent demand analysis

The `trip-log-service` exposes an endpoint that reads the real trip history from
**PostgreSQL**, builds a prompt with that data, and asks a language model to produce a
natural-language analysis of demand patterns.

**Example response:**

> "Based on 24 recorded trips on Ruta Parque, the 6:20–7:20 a.m. slot concentrates the
> highest demand with an average of 41 passengers per trip. Trips between 10:00 and 12:00
> show low occupancy (average 11 passengers). It is recommended to increase frequency in
> the early morning and reduce it in the midday slot."

### Endpoint

```
GET /trips/ai/demand-analysis
Authorization: Bearer <token>
```

### Internal logic

1. Query all trips from **PostgreSQL** via `storage/database.py`.
2. If there are no trips, return HTTP 400 with `{"detail": "Not enough data for analysis."}`.
3. Build a structured prompt from the real data: route, departure time, passenger count.
4. Send the prompt to the AI API.
5. Return the generated text with HTTP 200.
6. The frontend displays the analysis in the dashboard under an "Intelligent Analysis"
   section.

### Recommended AI APIs

| API               | Why use it                                         | Registration                                       |
| ----------------- | -------------------------------------------------- | -------------------------------------------------- |
| **Groq Cloud**    | Fast, generous free tier, OpenAI-compatible format | [console.groq.com](https://console.groq.com)       |
| **Google Gemini** | Wide free tier, good for structured text analysis  | [aistudio.google.com](https://aistudio.google.com) |
| **OpenRouter**    | Access to multiple models with a single API key    | [openrouter.ai](https://openrouter.ai)             |

### Implementation with Groq (Python)

```python
import httpx
from storage.database import get_all_trips  # reads from PostgreSQL

async def analyze_demand(db_session) -> str:
    trips = await get_all_trips(db_session)

    if not trips:
        raise ValueError("Not enough data for analysis.")

    lines = [
        f"- Route {t.route_id} | Bus {t.bus_id} | "
        f"Departure: {t.departure_time.strftime('%H:%M')} | "
        f"Passengers: {t.passenger_count}"
        for t in trips
    ]
    data_summary = "\n".join(lines)

    prompt = (
        f"Analyze the following university transport trip records and generate "
        f"concrete recommendations about demand distribution by time slot:\n\n"
        f"{data_summary}"
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-8b-8192",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a university transport analysis assistant. "
                            "Analyze bus occupancy data and generate clear, concise "
                            "recommendations in Spanish. Maximum 5 sentences."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 300
            }
        )
    return response.json()["choices"][0]["message"]["content"]
```

### Environment variable

```env
GROQ_API_KEY=gsk_...
```

Must be set in the local `.env` file and as a secret in Azure Container Apps. It must
never appear in source code or in the repository.

---

## Optional bonus — Asynchronous messaging

Not required. When a trip with high occupancy is registered (more than 80 passengers),
`trip-log-service` publishes an event to a queue. An independent worker consumes that
event and automatically triggers the AI analysis.

| Technology            | Azure option                                                  |
| --------------------- | ------------------------------------------------------------- |
| **RabbitMQ**          | Docker container locally + Azure Container Apps in the cloud  |
| **Azure Service Bus** | Managed service, Basic tier free                              |
| **Redis Streams**     | Docker container locally + Azure Cache for Redis in the cloud |

---

## Checklist — what must be working by May 22

```
Prerequisite — Database migration
[ ] trip-log-service migrated: in_memory.py removed, storage/database.py created
[ ] trips table created and functional in PostgreSQL
[ ] All trip-log-service endpoints read and write from the database

Containerization
[ ] Dockerfile for mini-identity-api
[ ] Dockerfile for trip-log-service
[ ] Multi-stage Dockerfile for the frontend (Nginx)
[ ] docker-compose.yml with all four services: postgres, auth, trip-log, frontend
[ ] postgres_data persistent volume configured in docker-compose.yml
[ ] docker-compose up --build starts everything without errors

Azure
[ ] Azure Database for PostgreSQL Flexible Server created and accessible
[ ] trip-log-service deployed on Azure Container Apps with DATABASE_URL pointing to Azure PostgreSQL
[ ] auth service deployed on Azure Container Apps
[ ] Frontend deployed on Azure Static Web Apps
[ ] Public URL verified and functional before the presentation date

AI
[ ] GET /trips/ai/demand-analysis endpoint implemented
[ ] Reads data from PostgreSQL (not from memory)
[ ] Model response visible in the frontend dashboard
[ ] GROQ_API_KEY configured as a secret environment variable

Full integration
[ ] End-to-end demo works on the Azure URL without depending on localhost
```
