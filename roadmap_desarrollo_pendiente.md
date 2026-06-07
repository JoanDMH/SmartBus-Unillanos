# SmartBus Unillanos — Roadmap de Tareas Pendientes
**Documento Técnico de Planificación** **Fecha:** Junio 2026  
**Proyecto:** Sistema Inteligente de Optimización del Servicio de Transporte (Ruta Universitaria Unillanos)  
**Curso:** Telemática I  
**Autores:** Joan David Martínez Hernández, Cristian Mateo Torres Villamil, Brayan David Mosquera Agudelo

> **Estado al 2026-06-07:** DEV-D3, DEV-A3, DEV-B1, DEV-B2, DEV-B3 y DEV-B4 completados en sesión anterior.
> Este documento lista únicamente las tareas pendientes.

---

## Orden de Prioridad de Ejecución

| Prioridad | ID | Justificación |
| :---: | :--- | :--- |
| 1 | DEV-E1 | El workflow de validación CI bloquea cualquier merge con modelo degradado. Debe existir antes de los próximos reentrenamientos. |
| 2 | DEV-A1 | El scheduler de limpieza nocturna es prerequisito para DEV-E2 y DEV-E3. |
| 3 | DEV-A2 | Evaluar TimescaleDB antes de que el volumen de datos haga lenta la BD; implementar alternativa si no está disponible. |
| 4 | DEV-C1 → DEV-C3 | Motor de optimización: depende de predicciones confiables (DEV-B4 ya operativo). |
| 5 | DEV-D1 | Dashboard con Recharts cobra sentido cuando hay predicciones que mostrar. |
| 6 | DEV-D2 | Human-in-the-loop depende de que el optimizador (DEV-C) genere horarios. |
| 7 | DEV-E2, DEV-E3 | MLOps de sostenibilidad: drift detection y reentrenamiento automático. |

---

## Módulo A: Pipelines de Ingesta y Estrategia de Datos

### DEV-A1 — Automatización ETL con APScheduler + GitHub Actions

**Componente:** `trip-log-service` (Backend)

Implementar dos niveles de automatización:

1. **Limpieza nocturna (APScheduler integrado en FastAPI):** Job que corre cada noche a las 02:00 UTC. Detecta y marca registros anómalos en la tabla `trips` (passenger_count = 0 sin nota, registros duplicados en ±5 min para el mismo bus, timestamps futuros). Genera un resumen de anomalías en el log de Azure Monitor.

2. **Reentrenamiento mensual (GitHub Actions cron):** Ver DEV-E3 — el scheduler de GHA dispara el `ai-engine` contra los datos del mes acumulado.

**Archivos a crear:**
- `trip-log-service/services/scheduler.py` — configuración APScheduler + job de limpieza

**Archivos a modificar:**
- `trip-log-service/main.py` — inicializar y arrancar el scheduler en el lifespan

---

### DEV-A2 — Optimización de Consultas Temporales en PostgreSQL

**Componente:** `storage/` (Base de Datos)

Evaluar la disponibilidad de **TimescaleDB** en la tier activa de Azure Database for PostgreSQL Flexible Server (suscripción Azure for Students). Si no está disponible:

- Crear índices compuestos: `CREATE INDEX idx_trips_route_time ON trips(route_id, departure_time DESC);`
- Crear vista materializada `trips_hourly_stats` que pre-agregue conteos por hora para acelerar las consultas del motor de predicción.
- Configurar refresh automático de la vista con `REFRESH MATERIALIZED VIEW CONCURRENTLY`.

**Archivos a crear:**
- `trip-log-service/storage/migrations/001_indexes.sql` — índices y vista materializada

---

## Módulo C: Motor Prescriptivo de Optimización de Frecuencias

> Prerequisito: DEV-B4 operativo (✅ completado).

### DEV-C1 — Motor de Programación Lineal (PuLP)

**Componente:** `optimization-service/optimizer.py` (Nuevo módulo)

Desarrollar el motor matemático con **PuLP**. La función objetivo minimiza el costo total de operación:

```
Minimizar: Σ (costo_combustible × km + costo_conductor × horas) × despachos[h]
Sujeto a:  capacidad[h] × despachos[h] ≥ demanda_predicha[h]   ∀h ∈ horas
```

Variables de decisión: número de buses despachados por franja horaria (entero ≥ 0).

---

### DEV-C2 — Restricciones Operativas

**Componente:** `optimization-service/constraints.py`

Codificar las restricciones duras del sistema en el modelo PuLP:
- Capacidad máxima por tipo de bus: 60 pasajeros (articulado) / 40 (estándar)
- Descanso obligatorio de conductores: mínimo 30 min cada 4 horas (normativa colombiana)
- Tiempo de recorrido Ruta Parque: 40 min ida + 40 min regreso
- Flota disponible de Servitranstur: parámetro configurable

---

### DEV-C3 — Endpoints de Itinerario

**Componente:** `trip-log-service/routers/optimization_router.py`

Crear dos endpoints:

- `POST /trips/optimization/weekly-schedule` — invoca `optimization-service`, persiste el itinerario resultado en una nueva tabla `schedules` en PostgreSQL, devuelve la grilla semanal en JSON.
- `GET /trips/optimization/weekly-schedule/latest` — devuelve el último itinerario aprobado, consumible por el frontend del despachador.

**Archivos a crear:**
- `trip-log-service/routers/optimization_router.py`
- `optimization-service/optimizer.py`
- `optimization-service/constraints.py`
- `optimization-service/requirements.txt` → `pulp>=2.8, httpx>=0.27`
- `optimization-service/Dockerfile`

---

## Módulo D: Evolución del Frontend

### DEV-D1 — PredictionDashboard (Recharts)

**Componente:** `frontend/src/pages/PredictionDashboard.jsx`

Rediseñar la sección de analíticas del Dashboard con **Recharts**:
- Gráfico de líneas dual: "Demanda Predicha (IA)" vs "Ocupación Real Observada" por hora del día
- Mapa de calor semanal de ocupación (heatmap por día × hora)
- Panel de métricas del modelo: MAE actual, última fecha de reentrenamiento, modelo activo (Prophet/XGBoost)

Nota: Se descarta Grafana embebido por complejidad de autenticación cross-origin con Azure Static Web Apps.

**Archivos a crear:**
- `frontend/src/pages/PredictionDashboard.jsx`
- `frontend/src/components/DemandChart.jsx`
- `frontend/src/api/predictionApi.js` → `getDemandPrediction(date, hour)`

**Archivos a modificar:**
- `frontend/src/App.jsx` → añadir ruta `/predictions`
- `frontend/src/pages/DashboardPage.jsx` → link al nuevo dashboard

---

### DEV-D2 — ScheduleApprovalPage (Human-in-the-loop)

**Componente:** `frontend/src/pages/ScheduleApprovalPage.jsx`

Módulo de gobernanza de horarios:
- Tabla editable del itinerario semanal generado por el optimizador
- Controles de aprobación / ajuste manual por franja horaria (número de buses)
- Botón "Confirmar grilla" que persiste la versión aprobada vía `POST /trips/optimization/weekly-schedule/approve`

**Archivos a crear:**
- `frontend/src/pages/ScheduleApprovalPage.jsx`
- `frontend/src/components/WeeklyScheduleTable.jsx`
- `frontend/src/api/optimizationApi.js`

---

## Módulo E: CI/CD Avanzado y MLOps

### DEV-E1 — Workflow de Validación ML en CI (GitHub Actions)

**Componente:** `.github/workflows/ml-validation.yml`

Añadir job al pipeline de CI que se ejecuta en cada PR a `Develop`:

```yaml
- name: Evaluate model
  run: |
    pip install -r ai-engine/requirements.txt
    python ai-engine/evaluate.py --model all
  # exit code 1 bloquea el merge automáticamente
```

El job descarga los artefactos `.pkl` desde Azure Blob, los evalúa contra `holdout_dataset.csv` y verifica MAE ≤ 5. Si falla, el PR queda bloqueado hasta corregir el pipeline de entrenamiento.

**Archivos a crear:**
- `.github/workflows/ml-validation.yml`

---

### DEV-E2 — Detección de Drift (APScheduler semanal)

**Componente:** `trip-log-service/services/scheduler.py` (ampliar DEV-A1)

Job semanal (lunes 03:00 UTC) que calcula:
- **Data drift**: prueba de Kolmogorov-Smirnov entre la distribución de `passenger_count` del último mes vs. la distribución del dataset de entrenamiento. Si p-value < 0.05, emite alerta en Azure Monitor.
- **Concept drift**: MAE de las últimas 200 predicciones vs. MAE de baseline del modelo. Si degradación > 15%, dispara notificación.

---

### DEV-E3 — Reentrenamiento Automático Mensual (GitHub Actions)

**Componente:** `.github/workflows/monthly-retrain.yml`

Workflow con `schedule: cron: '0 2 1 * *'` (primer día de cada mes, 02:00 UTC):

1. Ejecuta `ai-engine/train_prophet.py` y `ai-engine/train_xgboost.py` contra los últimos 3 meses de datos de PostgreSQL.
2. Ejecuta `ai-engine/evaluate.py` — si MAE ≤ 5, sube los nuevos `.pkl` a Azure Blob.
3. Reinicia el Container App `smartbus-trips` para que `model_loader.py` cargue los modelos actualizados en el próximo startup.

**Archivos a crear:**
- `.github/workflows/monthly-retrain.yml`
