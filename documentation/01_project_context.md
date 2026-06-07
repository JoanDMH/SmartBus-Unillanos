# SmartBus Unillanos — Project Context

> **Universidad de los Llanos · Facultad de Ciencias Básicas e Ingeniería**
> Curso: Telemática I · Villavicencio, Meta, Colombia — 2026
> Autores: Joan David Martínez Hernández · Cristian Mateo Torres Villamil · Brayan David Mosquera Agudelo

---

## 1. Executive Summary

SmartBus Unillanos is an AI-powered microservice designed to optimize the university transport system of Universidad de los Llanos (Unillanos) in Villavicencio, Meta. The project targets the **Ruta Parque** — the main corridor connecting campus with the city via fixed-interval buses — where uniform frequency scheduling does not match real passenger demand.

By collecting occupancy data and applying ML predictive models, the system anticipates demand per time slot and proposes **dynamic frequency schedules** that reduce low-occupancy trips, improve peak-hour service, and help the transport operator (Servitranstur) optimize operational costs.

Success on Ruta Parque serves as the **pilot case** before scaling to 10 neighborhood routes.

---

## 2. Problem

### Context

Unillanos operates 11 university transport routes managed by **Servitranstur**. The main route, Ruta Parque, runs the Barzal–Parque de los Estudiantes corridor with buses departing from 5:20 a.m. at regular 20-minute intervals until 7:10 p.m. on weekdays, and every 20 minutes until 6:00 p.m. on Saturdays.

### Core Problem

The **uniform frequency scheme** creates two simultaneous critical inefficiencies:

- **Underuse in off-peak hours:** buses run nearly empty, wasting fuel, driver time, and maintenance cost without proportional service.
- **Overcrowding in peak hours:** morning entry (6:20–7:20 a.m.) and afternoon exit (4:00–6:10 p.m.) concentrate the majority of users, potentially exceeding capacity and causing long wait times.

There is **no historical occupancy data** per trip. Without it, decisions cannot be made based on evidence.

### Impact

- **Students:** higher probability of missing buses at peak or finding empty vehicles off-peak.
- **Servitranstur:** non-optimized operational costs, greater fleet wear on low-productivity runs.
- **Unillanos:** degraded perception of transport as an institutional benefit.

---

## 3. Objectives

### General Objective

Develop and implement SmartBus Unillanos — an AI microservice that analyzes historical and real-time passenger volume on Ruta Parque, identifies demand patterns, and generates **dynamic frequency scheduling recommendations** that optimize service and reduce operational transport costs.

### Specific Objectives

1. Design and implement a per-trip occupancy data collection system (route, date, time).
2. Build a clean, labeled historical data repository ready for model training.
3. Develop and validate demand prediction models (time-series + classification) with **accuracy ≥ 85%**.
4. Create a frequency optimization engine that proposes dynamic weekly schedules based on predictions.
5. Develop a REST API (microservice) exposing predictions and recommendations to UIs or external systems.
6. Design a monitoring dashboard for Servitranstur operators and Unillanos administration.
7. Validate the pilot model on Ruta Parque for at least one full academic semester.
8. Document the architecture to facilitate replication across the 10 neighborhood routes.

---

## 4. Scope

### In Scope — Pilot Phase

- Ruta Parque in its full route (Parque de los Estudiantes → Unillanos campus and return).
- Data collection Monday through Saturday, for all scheduled trips.
- Predictive models by time slot and day of week.
- Seasonal variables: exam weeks, semester start/end, holidays, rainy days.
- REST API documented with Swagger/OpenAPI.
- Basic web dashboard for KPI visualization and recommendations.

### Out of Scope — Pilot Phase

- Neighborhood routes (Covisan, Maracos, Terminal, Villacentro, Viva, La Grama, Porfía, Montecarlo/Amarilo, Postobón, Reliquia) — planned for post-pilot scaling.
- Integration with electronic payment systems or turnstiles.
- Mobile app for end users (possible future extension).
- Automatic dispatch control without human intervention.

---

## 5. Ruta Parque — Current Schedule

- Operates **Monday to Saturday**.
- Buses depart from **Parque de los Estudiantes** (city side) starting at **5:20 a.m.** every **20 minutes**.
- Last departure from the city: **5:20 p.m.** (weekdays), **6:00 p.m.** (Saturdays).
- Return buses depart from **campus (frente a la piscina de Unillanos)** also every 20 minutes until **7:10 p.m.** (weekdays).
- **Stop locations:** Parque de los Estudiantes · paradero buses públicos Unicentro · Tecniguayas · frente al Colegio Industrial · paradero de buses de Makro · paradero de buses públicos de La Alborada · puente peatonal frente a la Universidad Cooperativa · bomba Primax · entrada Barcelona.

---

## 6. 10 Neighborhood Routes — Overview

Each neighborhood route has fixed departure times from the neighborhood and fixed return times from campus.

| Route | Pickup Point | Departures from neighborhood | Departures from campus |
|---|---|---|---|
| Covisan | Frente a Droguería Estero 24 hrs | 5:10, 6:10, 7:10, 8:20 a.m. / 1:20 p.m. | 11:00 a.m., 12:00 m, 4:00, 5:00, 6:10 p.m. |
| Maracos | Montallantas bomba av. Maracos | 5:10, 6:10, 7:10, 8:20 a.m. / 1:20 p.m. | 11:00 a.m., 12:00 m, 4:00, 5:00, 6:10 p.m. |
| Terminal | Frente al Banco W de Hato Grande | 5:20, 6:20, 7:20, 8:20 a.m. / 1:20 p.m. | 11:00 a.m., 12:00 m, 4:00, 5:00, 6:10 p.m. |
| Villacentro | Portería principal C.C. Villacentro | 5:20, 6:20, 7:20, 8:20 a.m. / 1:20 p.m. | 11:00 a.m., 12:00 m, 4:00, 5:00, 6:10 p.m. |
| Viva | Semáforo C.C. Viva, vía Villabolivar | 5:20, 6:20, 7:20, 8:20 a.m. / 1:20 p.m. | 11:00 a.m., 12:00 m, 4:00, 5:00, 6:10 p.m. |
| La Grama | En 4 parques / Picadas y algo más | 5:20, 6:20, 7:20, 8:20 a.m. / 1:20 p.m. | 11:00 a.m., 12:00 m, 4:00, 5:00, 6:10 p.m. |
| Porfía | Entrada aptos de La Madrid | 5:10, 7:10, 8:20 a.m. / 1:20 p.m. | 12:00 m, 5:00, 6:10 p.m. |
| Montecarlo/Amarilo | Glorieta entrada a La Rochela | 5:20, 6:20, 7:20, 8:20 a.m. / 1:20 p.m. | 11:00 a.m., 12:00 m, 4:00, 5:00, 6:10 p.m. |
| Postobón | Centro Comercial Sinfonía | 5:20, 6:20, 7:20, 8:20 a.m. / 1:20 p.m. | 11:00 a.m., 12:00 m, 4:00, 5:00, 6:10 p.m. |
| Reliquia | Puesto de salud de La Reliquia | 5:10, 7:10 a.m. | 5:00, 6:10 p.m. |

---

## 7. System Architecture

### High-Level Overview

SmartBus Unillanos uses a **decoupled microservice architecture** with four independent functional layers communicating via REST APIs and async messaging.

| Layer | Component | Responsibility |
|---|---|---|
| Collection | Capture Agent | Register passengers per trip (manual app / sensor) |
| Storage | Historical Database | PostgreSQL + TimescaleDB for time-series |
| Intelligence | Prediction Engine + Optimizer | ML models (LSTM / Prophet + linear programming) |
| Presentation | REST API + Dashboard | FastAPI (Python) + React frontend |

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                             │
│              (dashboard for operators)                      │
└────────────┬──────────────────────────┬────────────────────┘
             │                          │
             ▼                          ▼
┌────────────────────┐     ┌────────────────────────────────┐
│   Auth Service     │     │      trip-log-service          │
│   (MiniIdentity)   │     │  - register trips              │
│   .NET 10          │     │  - query occupancy history     │
└────────────────────┘     └────────────────────────────────┘
                                        │
                                        ▼
                           ┌────────────────────────────────┐
                           │     prediction-service         │
                           │  - ML demand forecasting       │
                           │  - Prophet / LSTM / XGBoost    │
                           └────────────────────────────────┘
                                        │
                                        ▼
                           ┌────────────────────────────────┐
                           │     scheduler-service          │
                           │  - frequency optimization      │
                           │  - weekly schedule proposals   │
                           └────────────────────────────────┘
                                        │
                                        ▼
                           ┌────────────────────────────────┐
                           │     PostgreSQL + TimescaleDB   │
                           │  (time-series optimized)       │
                           └────────────────────────────────┘
```

### Data Flow

1. A driver or validator registers occupancy at trip start via a lightweight **offline-capable PWA** (syncs when signal is available).
2. Data is sent to the ingestion service and stored with timestamp, route, bus ID, and passenger count.
3. Each night an **automated pipeline** (Apache Airflow / Celery) retrains or adjusts models with the day's new data.
4. The optimization engine runs in **weekly windows** and generates a frequency proposal for the next week.
5. Operators review and approve (or adjust) recommendations via the dashboard before implementation.

---

## 8. Microservices — Final Scope

### trip-log-service (Python · FastAPI)
Core data collection layer. Records per-trip occupancy. Stores: route, bus, departure time, passenger count, weather, academic week, special events. This is the dataset that feeds the prediction models.

### prediction-service (Python · FastAPI)
Trains and serves ML models on the trip log data. Models: Prophet or SARIMA for time-series demand forecasting, LSTM for non-linear long-term patterns, XGBoost/LightGBM for demand level classification (High / Medium / Low). Retrains nightly via Airflow/Celery pipeline.

### scheduler-service (Python · FastAPI)
Consumes predictions and runs a linear programming optimizer (PuLP/SciPy) to propose an optimal frequency schedule for the upcoming week. Minimizes operational cost while maintaining service quality thresholds.

### auth-service (MiniIdentity · .NET 10)
Provided externally. Handles user registration, login, role management, and JWT issuance. All other services validate JWT tokens independently using the shared secret key.

---

## 9. Key Design Decisions

- **No shared database between services.** Each service owns its data.
- **JWT validation is decentralized.** Every service that requires auth verifies the token independently using the shared secret — no calls back to the auth service.
- **Frontend is the orchestrator.** Services do not call each other; the frontend coordinates them.
- **Cold start strategy.** Before any ML model is trained, data must be collected manually for at least 2 months. The `trip-log-service` exists precisely to enable this.
- **Pilot-first.** All development targets Ruta Parque first. Scaling to neighborhood routes only requires adding new `route_id` values — no structural changes.

---

## 10. Data Model — Core Trip Record

```
Trip {
  id              UUID
  route_id        string        -- e.g. "PARQUE", "COVISAN"
  bus_id          string        -- vehicle identifier
  departure_time  datetime      -- actual departure timestamp
  passenger_count integer       -- 0–100
  day_type        enum          -- WEEKDAY | SATURDAY | HOLIDAY
  academic_week   integer       -- week number in semester (1–18)
  weather         enum          -- SUNNY | CLOUDY | RAINY
  special_event   boolean       -- exams week, semester start, etc.
  registered_by   string        -- username from JWT claim
  created_at      datetime
}
```

---

## 11. AI / ML Component

### Input Features

- Hour of day and day of week.
- Academic semester week (start, midterm, exams, end).
- Weather condition (rainy / sunny) — sourced from a weather API.
- Occupancy history for the last N trips in the same time slot.
- Special events from the Unillanos academic calendar.

### Models

| Model | Purpose | Tool |
|---|---|---|
| Prophet / SARIMA | Demand forecasting per time slot | Python: Prophet (Meta), statsmodels |
| LSTM / GRU | Capture non-linear patterns in long series | PyTorch / TensorFlow |
| Gradient Boosting | Demand level classification (High / Medium / Low) | XGBoost / LightGBM |
| Schedule Optimizer | Optimal frequency proposals minimizing cost and maximizing service | SciPy / PuLP (integer linear programming) |

### Evaluation Metrics

- MAE / RMSE for demand prediction.
- Precision, recall, and F1-score for demand level classification.
- Percentage reduction of empty seats on off-peak trips.
- Reduction of average wait time during peak hours.
- Estimated fuel savings and cost per transported passenger.

---

## 12. Data Strategy

### Cold Start — Initial Collection

For the **first two months**, drivers or a designated validator will manually log passenger counts at each trip start using an **offline-capable PWA** (React or Flutter) that syncs data when connectivity is available. This bootstrapping mechanism is critical to build the training dataset.

### Dataset Structure

| Field | Type | Description |
|---|---|---|
| trip_id | UUID | Unique trip identifier |
| timestamp_departure | TIMESTAMP | Departure date and time from origin |
| route_id | VARCHAR | Route identifier (e.g. PARQUE) |
| bus_id | VARCHAR | Vehicle identifier |
| passenger_count | INTEGER | Number of passengers on the trip |
| day_type | ENUM | Weekday, Saturday, Holiday |
| academic_week | INTEGER | Semester week number (1–18 approx.) |
| weather | ENUM | Sunny, Rainy, Cloudy |
| special_event | BOOLEAN | Exams, semester start, etc. |

### Privacy and Data Governance

The system does **not collect personal student data** — only aggregated passenger counts per trip. Data is owned by Universidad de los Llanos and stored on local or institutional cloud servers in compliance with **Ley 1581 de 2012 (Habeas Data)**.

---

## 13. Tech Stack

| Area | Technology | Justification |
|---|---|---|
| Auth service | .NET 10 · ASP.NET Core | External provider (MiniIdentity) |
| Domain microservices | Python 3.11+ · FastAPI · Uvicorn | High performance, typed, auto Swagger docs |
| ML / prediction | scikit-learn · XGBoost · Prophet · PyTorch | Mature ecosystem, MLflow-compatible |
| Scheduler / optimizer | PuLP · SciPy | Integer linear programming |
| Database (final) | PostgreSQL · TimescaleDB | Time-series optimized, open source |
| Pipeline orchestration | Apache Airflow or Celery | Automated retraining and reporting pipelines |
| Frontend / Dashboard | React · Vite · Recharts / Grafana | Interactive KPI and prediction visualization |
| Capture app | PWA (React) / Flutter | Offline functionality, no app store required |
| MLOps / Versioning | MLflow · Git | Experiment traceability and model versioning |
| Containerization | Docker · docker-compose | Portability, easy university server deployment |

---

## 14. Work Plan & Timeline

| Phase | Main Activities | Duration | Deliverable |
|---|---|---|---|
| **Phase 0** | Requirements gathering, Servitranstur agreements, KPI definition | 2 weeks | Project charter |
| **Phase 1** | DB design, capture app development, bus installation, data collection start | 6 weeks | App + active DB |
| **Phase 2** | EDA of initial dataset, feature engineering, baseline model training | 4 weeks | Models v1 |
| **Phase 3** | Frequency optimizer, REST API development, component integration | 4 weeks | Microservice v1 |
| **Phase 4** | Monitoring dashboard, operator user testing, adjustments | 3 weeks | Dashboard + API docs |
| **Phase 5** | Production pilot (full academic semester), monitoring, monthly retraining | 18 weeks | Impact report |
| **Phase 6** | Results evaluation, neighborhood route scaling documentation | 2 weeks | Scaling manual |

**Total estimated pilot duration: ~10 months.**

---

## 15. KPIs / Success Indicators

| Indicator | Baseline | Target at Pilot End |
|---|---|---|
| Demand prediction accuracy | — | ≥ 85% (MAE ≤ 5 pax) |
| % trips with occupancy < 20% during regular schedule | To be measured (Phase 1) | Reduction ≥ 30% |
| Average wait time at peak (6:20–7:20 a.m.) | To be measured (Phase 1) | Reduction ≥ 20% |
| User satisfaction (semester survey) | To be measured (Phase 0) | Increase ≥ 15% |
| Estimated fuel savings | — | ≥ 10% over baseline |

---

## 16. Risk Management

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Low driver adherence to data registration | High | High | Incentive protocol, weekly supervision, simplified app UX |
| Insufficient data for cold-start training | Medium | High | Intensive manual collection for 2 months before modeling |
| Operator resistance to change | Medium | Medium | Socialization workshops, demonstrate concrete economic benefits |
| Extreme variability from short academic semester | Low | Medium | Include academic week indicator as a key feature |
| Lack of university IT infrastructure | Medium | High | Cloud deployment (AWS/GCP free tier) as fallback |

---

## 17. Scaling Roadmap

Once the Ruta Parque pilot is validated, adding a new `route_id` value is sufficient to onboard a neighborhood route — **no structural changes** to models or API are needed.

### Wave 1 — High fixed-frequency routes
Covisan · Maracos · Terminal · Villacentro · Viva
These share the same schedule structure as Ruta Parque and integrate directly into the existing pipeline.

### Wave 2 — Reduced or special-frequency routes
La Grama · Porfía · Montecarlo/Amarilo · Postobón · Reliquia
Require optimizer adjustments due to lower frequency and specific stop characteristics.

### Long-Term Horizon
Integration with **IoT sensors** (automatic passenger counters) to eliminate manual registration dependency and enable **real-time intra-day dynamic adjustments**.

---

## 18. Scalability Path (Development Phases)

1. **Phase 1 (pilot):** Ruta Parque only. Manual data collection. In-memory storage. No ML yet.
2. **Phase 2 (data):** 2 months of trip data collected. First ML models trained. Predictions validated against reality.
3. **Phase 3 (optimize):** Scheduler service deployed. First dynamic frequency proposals generated and reviewed by operators.
4. **Phase 4 (scale):** Neighborhood routes onboarded one by one. IoT passenger counters considered to replace manual registration.
