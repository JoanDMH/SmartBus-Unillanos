# SmartBus Unillanos — MVP Specification

## What This MVP Is

A functional microservices-based web application with three components:

1. **Frontend** — React app with login and a post-login dashboard.
2. **Auth service** — MiniIdentity API (provided, .NET 10). Not built by the team.
3. **trip-log-service** — New FastAPI microservice. Records and queries per-trip passenger counts for Ruta Parque.

The MVP demonstrates: user authentication, protected routes, and a working domain flow (register a trip → view trip history).

---

## Architecture

```
Browser
  │
  ├─── POST /api/auth/login ──────────────► MiniIdentity API (.NET 10)
  │                                         localhost:5000
  │         ◄── JWT token ─────────────────┘
  │
  ├─── GET  /routes ──────────────────────► trip-log-service (FastAPI)
  ├─── POST /trips   (Bearer JWT) ────────► localhost:8000
  ├─── GET  /trips   (Bearer JWT) ────────►
  └─── GET  /trips/stats/summary (Bearer) ►
```

**Rules:**
- The frontend stores the JWT and attaches it to every `trip-log-service` request.
- `trip-log-service` validates the JWT independently (same secret key, no call back to MiniIdentity).
- The two backend services never call each other.
- All data is stored in memory (no database required).

---

## Repository Structure

```
smartbus-unillanos/
├── README.md
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api/
│       │   ├── authApi.js
│       │   └── tripApi.js
│       ├── context/
│       │   └── AuthContext.jsx
│       └── pages/
│           ├── LoginPage.jsx
│           ├── DashboardPage.jsx
│           ├── RegisterTripPage.jsx
│           └── TripHistoryPage.jsx
└── trip-log-service/
    ├── requirements.txt
    ├── .env.example
    ├── main.py
    ├── config.py
    ├── auth/
    │   └── jwt_validator.py
    ├── routers/
    │   ├── routes_router.py
    │   └── trips_router.py
    ├── models/
    │   ├── route.py
    │   └── trip.py
    └── storage/
        └── in_memory.py
```

---

## MiniIdentity API — What the Frontend Uses

Base URL: `http://localhost:5000`

The auth service is already built. The frontend only needs these two endpoints:

**POST `/api/auth/register`**
```json
// request body
{ "username": "string", "email": "string", "password": "string" }

// response 200
{ "id": "uuid", "username": "string", "email": "string" }
```

**POST `/api/auth/login`**
```json
// request body
{ "usernameOrEmail": "string", "password": "string" }

// response 200
{ "token": "eyJ..." }
```

The returned `token` is a JWT signed with this key (from `appsettings.json`):
```
Key:      THIS_IS_A_DEMO_KEY_CHANGE_IT_123456789
Issuer:   MiniIdentityApi
Audience: MiniIdentityApiUsers
```

The `trip-log-service` must use these same values to validate tokens.

---

## trip-log-service — Full Specification

### Environment variables (`.env`)
```
JWT_SECRET=THIS_IS_A_DEMO_KEY_CHANGE_IT_123456789
JWT_ISSUER=MiniIdentityApi
JWT_AUDIENCE=MiniIdentityApiUsers
PORT=8000
```

### Dependencies (`requirements.txt`)
```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
pyjwt>=2.8.0
python-dotenv>=1.0.0
```

### How to run
```bash
cd trip-log-service
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```

Swagger UI available at `http://localhost:8000/docs`.

---

### `main.py`

- Create the FastAPI app.
- Add CORS middleware allowing all origins (for local development).
- Include `routes_router` and `trips_router`.

---

### `config.py`

Load environment variables with `python-dotenv`. Expose:
- `JWT_SECRET: str`
- `JWT_ISSUER: str`
- `JWT_AUDIENCE: str`

---

### `auth/jwt_validator.py`

FastAPI dependency that protects endpoints. Logic:

1. Extract Bearer token from `Authorization` header. Return `401` if missing.
2. Decode and verify the JWT using `pyjwt` with `JWT_SECRET`, `JWT_ISSUER`, `JWT_AUDIENCE`, and algorithm `HS256`.
3. Return the `sub` claim (username string) if valid.
4. Return `401` with message `"Invalid or expired token"` if verification fails.

This function is used as `Depends(get_current_user)` on protected routes.

---

### `storage/in_memory.py`

A module-level list `trips_db: list[dict] = []`.

Implement these four functions:

```python
def save_trip(trip: dict) -> dict:
    # append to trips_db, return the trip

def get_all_trips(route_id: str | None = None, date: str | None = None) -> list[dict]:
    # return all trips, optionally filtered
    # date filter format: "YYYY-MM-DD", match against departure_time date part

def get_trip_by_id(trip_id: str) -> dict | None:
    # return trip where id == trip_id, or None

def compute_stats() -> dict:
    # return:
    # {
    #   "total_trips": int,
    #   "average_passengers": float,       -- rounded to 1 decimal
    #   "max_passengers": int,
    #   "min_passengers": int,
    #   "busiest_hour": str                -- "HH:MM" of the hour with most avg passengers
    # }
    # if trips_db is empty, return all zeros and busiest_hour as null
```

---

### `models/route.py`

```python
class RouteInfo(BaseModel):
    id: str
    name: str
    description: str
    schedule: list[str]   # list of "HH:MM" strings
```

---

### `models/trip.py`

```python
class TripCreate(BaseModel):
    route_id: str
    departure_time: datetime
    passenger_count: int = Field(ge=0, le=100)
    bus_id: str
    notes: str | None = None

class TripResponse(BaseModel):
    id: str
    route_id: str
    departure_time: datetime
    passenger_count: int
    bus_id: str
    notes: str | None
    registered_by: str       # username extracted from JWT
    created_at: datetime
```

---

### `routers/routes_router.py`

**`GET /routes`** — public, no auth required.

Returns a hardcoded list with one route:

```json
[
  {
    "id": "PARQUE",
    "name": "Ruta Parque",
    "description": "Parque de los Estudiantes → Campus Unillanos",
    "schedule": [
      "05:20","05:40","06:00","06:20","06:40","07:00","07:20",
      "07:40","08:00","08:20","08:40","09:00","09:20","09:40",
      "10:00","10:20","10:40","11:00","11:20","11:40","12:00",
      "12:20","12:40","13:00","13:20","13:40","14:00","14:20",
      "14:40","15:00","15:20","15:40","16:00","16:20","16:40",
      "17:00","17:20"
    ]
  }
]
```

---

### `routers/trips_router.py`

All endpoints require auth via `Depends(get_current_user)`.

---

**`POST /trips`** — create a trip record.

- Receive `TripCreate` body.
- Generate a UUID for `id`.
- Set `registered_by` from the current user (JWT `sub` claim).
- Set `created_at` to `datetime.utcnow()`.
- Call `save_trip()`.
- Return `TripResponse` with HTTP 201.

---

**`GET /trips`** — list all trips.

- Optional query params: `route_id: str`, `date: str` (format `YYYY-MM-DD`).
- Call `get_all_trips(route_id, date)`.
- Return `list[TripResponse]` with HTTP 200.

---

**`GET /trips/stats/summary`** — occupancy statistics.

- Call `compute_stats()`.
- Return the stats dict with HTTP 200.

> ⚠️ This route must be defined **before** `GET /trips/{trip_id}` in the router to avoid FastAPI matching `"stats"` as a path parameter.

---

**`GET /trips/{trip_id}`** — get a single trip.

- Call `get_trip_by_id(trip_id)`.
- Return `TripResponse` if found, HTTP 404 with `{"detail": "Trip not found"}` if not.

---

## Frontend — Full Specification

### Tech stack
- React 18 + Vite
- React Router v6
- No UI component library required (plain HTML/CSS is fine)

### How to run
```bash
cd frontend
npm install
npm run dev
# runs at http://localhost:5173
```

---

### Route map

| Path | Component | Access |
|---|---|---|
| `/login` | LoginPage | Public. Redirect to `/dashboard` if already logged in. |
| `/dashboard` | DashboardPage | Private. Redirect to `/login` if no token. |
| `/trips` | TripHistoryPage | Private. |
| `/trips/new` | RegisterTripPage | Private. |
| `/` | — | Redirect to `/dashboard` |

A `PrivateRoute` wrapper component checks for a token in `AuthContext`. If absent, redirects to `/login`.

---

### `context/AuthContext.jsx`

Provides:
- `token: string | null` — the JWT string.
- `user: string | null` — the username (decoded from JWT `sub` claim, or from login response).
- `login(token)` — saves token to state and `localStorage` under key `smartbus_token`.
- `logout()` — clears state and `localStorage`, redirects to `/login`.

On app load, initialize `token` from `localStorage.getItem("smartbus_token")` if present.

---

### `api/authApi.js`

Base URL: `http://localhost:5000/api`

```javascript
// POST /auth/login
// body: { usernameOrEmail, password }
// returns: { token: string }
// throws Error with message if request fails
export async function loginUser(usernameOrEmail, password) { ... }
```

---

### `api/tripApi.js`

Base URL: `http://localhost:8000`

Every function receives `token` as first argument and sets `Authorization: Bearer <token>` header.

```javascript
// GET /routes — no auth needed
export async function getRoutes() { ... }

// GET /trips?route_id=...&date=...
export async function getTrips(token, { routeId, date } = {}) { ... }

// POST /trips
// body: { route_id, departure_time, passenger_count, bus_id, notes }
export async function createTrip(token, tripData) { ... }

// GET /trips/stats/summary
export async function getTripStats(token) { ... }
```

---

### `pages/LoginPage.jsx`

- Form with two fields: `usernameOrEmail`, `password`.
- On submit: call `loginUser()`, then call `login(token)` from context, then navigate to `/dashboard`.
- Show inline error message if login fails.
- If already authenticated, redirect to `/dashboard`.

---

### `pages/DashboardPage.jsx`

On mount:
- Call `getRoutes()` — display each route as a card showing name, description, and schedule.
- Call `getTripStats(token)` — display a summary panel with: total trips, average passengers, busiest hour.

UI elements:
- "Register Trip" button → navigates to `/trips/new`.
- "View History" button → navigates to `/trips`.
- "Logout" button → calls `logout()` from context.

---

### `pages/RegisterTripPage.jsx`

Form fields:
- `route_id` — `<select>` populated from `getRoutes()`.
- `departure_time` — `<input type="datetime-local">`.
- `passenger_count` — `<input type="number" min="0" max="100">`.
- `bus_id` — `<input type="text">`.
- `notes` — `<textarea>` (optional).

On submit:
- Call `createTrip(token, formData)`.
- On success, navigate to `/trips`.
- On error, show error message inline.

---

### `pages/TripHistoryPage.jsx`

On mount: call `getTrips(token)`.

Display results in a table with columns:
- Route
- Bus
- Departure Time (formatted as readable date + time)
- Passengers
- Registered By

Show "No trips registered yet." if the list is empty.

Include a "Back to Dashboard" link.

---

## Demo Flow (end to end)

1. Open `http://localhost:5173`.
2. Redirected to `/login`.
3. Enter credentials of a user registered in MiniIdentity.
4. Login succeeds → redirected to `/dashboard`.
5. Dashboard shows Ruta Parque card and stats (all zeros initially).
6. Click "Register Trip" → fill form → submit.
7. Redirected to `/trips` → table shows the registered trip.
8. Go back to dashboard → stats now reflect the registered trip.

---

## What This MVP Does Not Include

These are intentionally out of scope:

- ML prediction or demand forecasting
- Frequency optimization
- Role-based access (Admin vs Driver)
- Persistent database (everything resets on service restart)
- Multiple routes (only Ruta Parque)
- Weather or academic calendar fields on trip registration
- Docker or deployment configuration
