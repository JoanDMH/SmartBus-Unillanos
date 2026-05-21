# SmartBus Unillanos — MVP Walkthrough (Hito 2)

Esta guía documenta la arquitectura final, la estructura del proyecto y los resultados de verificación para el **Hito 2** de **SmartBus Unillanos**. 

En este hito, el proyecto migró de almacenamiento en memoria a **PostgreSQL persistente**, se integró un modelo de lenguaje en la nube a través de **Groq Cloud API** para el análisis inteligente de demanda, y toda la solución fue **contenedorizada** mediante Docker y Docker Compose para facilitar su portabilidad y despliegue.

---

## 🏗️ Arquitectura de Servicios (Local)

El sistema completo se ejecuta de forma coordinada a través de contenedores locales Docker conectados a una misma red virtual.

| Componente | Tecnología | Puerto Local | Descripción / Rol |
|---|---|---|---|
| **postgres** | PostgreSQL 15 | `5432` | Base de datos relacional para el almacenamiento persistente de viajes. |
| **auth** | .NET 10 · ASP.NET Core | `5000` | Microservicio externo provisto (MiniIdentity) para emisión y validación de credenciales JWT. |
| **trip-log-service** | Python 3.11 · FastAPI | `8000` | Microservicio del Hito 2. Registra recorridos, expone estadísticas y consume Groq API. |
| **frontend** | React 19 · Vite · Nginx | `80` (Producción)<br>`5173` (Vite Dev) | Aplicación web en modo oscuro para conductores y administradores de Servitranstur. |

---

## 📁 Estructura General del Proyecto

El repositorio consolidado para el Hito 2 tiene la siguiente distribución:

```
SmartBus-Unillanos/
├── .env                          ← Clave GROQ_API_KEY para docker-compose (gitignored)
├── .gitignore                    ← Reglas de exclusión para venv, node_modules y .env
├── docker-compose.yml            ← Orquestación de los 4 contenedores
├── Dockerfile.auth               ← Compilación multi-etapa para el servicio .NET 10
├── README.md                     ← Documentación general del repositorio
├── technical_guide_milestone2.md  ← Guía técnica de requerimientos
│
├── mini-identity-api-dotnet/     ← Submódulo del servicio Auth
│   ├── .dockerignore
│   └── src/...
│
├── trip-log-service/             ← Microservicio de Viajes (FastAPI)
│   ├── Dockerfile                ← Imagen ligera basada en Python 3.11-slim
│   ├── .dockerignore
│   ├── requirements.txt          ← Contiene sqlalchemy, asyncpg, alembic y httpx
│   ├── config.py                 ← Carga y valida variables de entorno
│   ├── main.py                   ← Ciclo de vida (lifespan) que inicializa la DB
│   ├── auth/jwt_validator.py     ← Autenticación descentralizada mediante JWT
│   ├── models/trip.py            ← Modelos Pydantic (Weather enum, TripCreate, TripResponse)
│   ├── routers/trips_router.py   ← Endpoints CRUD + estadísticas + análisis IA
│   ├── services/ai_analysis.py   ← Integración con Groq API (llama-3.1-8b-instant)
│   └── storage/database.py       ← Capa SQLAlchemy ORM Asíncrona (TripRow, CRUD helpers)
│
└── frontend/                     ← Aplicación Web (React + Nginx)
    ├── Dockerfile                ← Compilación Vite (Stage 1) -> Servidor Nginx (Stage 2)
    ├── nginx.conf                ← Proxy reverso para evitar CORS y SPA Routing
    ├── package.json              ← react 19, react-router-dom 7, vite 8
    └── src/
        ├── main.jsx
        ├── App.jsx               ← Enrutamiento y control de rutas privadas
        ├── index.css             ← Estilos premium en modo oscuro + tarjetas de IA
        ├── api/tripApi.js        ← Conexión de endpoints (getDemandAnalysis)
        └── pages/
            ├── DashboardPage.jsx ← Resumen, rutas y sección de "Análisis Inteligente"
            ├── RegisterTripPage.jsx ← Formulario extendido con variables contextuales (ML)
            └── TripHistoryPage.jsx  ← Historial estructurado con descarga de CSV
```

---

## 🚀 Cómo Ejecutar el Sistema Completo

### Método Recomendado (Docker Compose)

Este método levanta todos los servicios, los conecta en red y configura las rutas de proxy reverso en Nginx automáticamente.

1. **Configurar las credenciales**:
   Crea un archivo `.env` en la raíz del proyecto (`SmartBus-Unillanos/`) con la clave de Groq:
   ```env
   GROQ_API_KEY=gsk_your_groq_api_key_here
   ```

2. **Compilar e Iniciar**:
   Ejecuta el siguiente comando en tu terminal desde la raíz del proyecto:
   ```bash
   docker compose up --build
   ```

3. **Acceder a la aplicación**:
   - Frontend (React + Nginx): [http://localhost](http://localhost) (Puerto 80)
   - API de Autenticación (.NET): [http://localhost:5000](http://localhost:5000)
   - API de Viajes (FastAPI): [http://localhost:8000](http://localhost:8000)
   - Swagger de Viajes: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔑 Características Principales de la Implementación (Hito 2)

### 1. Persistencia Persistente en PostgreSQL (Requerimiento 0)
- **Tecnología**: SQLAlchemy 2.0 en modo asíncrono (`async_sessionmaker`, `create_async_engine`) junto al driver de alta velocidad `asyncpg`.
- **Control de Zona Horaria**: Se implementaron columnas `DateTime(timezone=True)` en la tabla `trips` para evitar errores de desfase horario (`offset-naive vs offset-aware`) cuando el navegador envía fechas con huso horario ISO.
- **Volumen Persistente**: Configuración de `postgres_data` en Docker Compose para asegurar que los datos no se borren en caso de reiniciar los contenedores.

### 2. Contenedores Optimizados (Requerimiento 1)
- **Frontend Nginx**: Se utiliza un Dockerfile multi-etapa. Nginx se encarga de servir los archivos estáticos generados por la compilación de Vite y actúa como **proxy reverso** local:
  - Las llamadas a `/api/*` se redirigen a `http://auth:5000/*`
  - Las llamadas a `/routes` y `/trips` se redirigen a `http://trip-log:8000/*`
  - Esto elimina por completo los problemas de CORS durante la ejecución local.

### 3. Análisis de Demanda con Inteligencia Artificial (Requerimiento 3)
- **API**: Integración con Groq Cloud API mediante `httpx.AsyncClient`.
- **Modelo**: `llama-3.1-8b-instant` (actualizado debido a la depreciación del modelo anterior y para evitar límites de payload en claves gratuitas).
- **Lógica**: Lee el historial de viajes de PostgreSQL en tiempo real y toma los **30 registros más recientes** para evitar errores de tamaño de payload (`413 Payload Too Large`) en la API gratuita de Groq. Con estos datos, genera un prompt estructurado (incluyendo variables como clima, semana académica y eventos especiales) y obtiene un análisis ejecutivo en español de máximo 5 oraciones con sugerencias de optimización.

---

## 🔬 Resultados de Verificación Local

### 1. Swagger UI de Viajes (`http://localhost:8000/docs`)
Los 7 endpoints se exponen correctamente y el nuevo endpoint de análisis de IA está protegido por Bearer JWT:

| Método | Ruta | Seguridad | Descripción |
|---|---|---|---|
| `GET` | `/` | Público | Health Check del microservicio. |
| `GET` | `/routes` | Público | Lista la Ruta Parque y sus horarios. |
| `POST` | `/trips` | Bearer JWT | Registra un nuevo viaje con variables contextuales. |
| `GET` | `/trips` | Bearer JWT | Lista todos los viajes filtrados opcionalmente. |
| `GET` | `/trips/stats/summary` | Bearer JWT | Calcula promedios, máximos y horas pico. |
| `GET` | `/trips/ai/demand-analysis` | Bearer JWT | Genera el reporte de ocupación con Groq. |
| `GET` | `/trips/{trip_id}` | Bearer JWT | Obtiene los detalles de un viaje específico. |

---

## 🎬 Flujo de Demostración E2E (Paso a Paso)

Para verificar el correcto funcionamiento del Hito 2 en tu máquina, sigue este flujo lógico:

1. **Registrar un Usuario**:
   Dado que la base de datos de usuarios de MiniIdentity se inicializa vacía en memoria, regístrate haciendo un POST a `http://localhost:5000/api/auth/register` (vía Postman/curl) o utiliza el flujo en la app web si implementa la pestaña.
   
2. **Iniciar Sesión**:
   Abre `http://localhost` e ingresa tus credenciales. La aplicación normalizará el token de MiniIdentity (`accessToken`), lo guardará en `localStorage` y te dará acceso al panel de control.

3. **Diligenciar un Viaje**:
   Ve a **"Registrar Viaje"** y completa el formulario. Notarás dos secciones visuales diferenciadas:
   - **Datos del viaje**: Ruta, fecha/hora, pasajeros y número del bus.
   - **Variables de contexto**: Selector de Clima, Selector de Semana Académica (de 1 a 18 con hitos clave marcados como "Parciales" o "Finales") y casilla de Evento Especial.

4. **Verificar Persistencia**:
   Tras registrar el viaje, verás la tabla de historial de forma inmediata con insignias de colores según el clima. Si ejecutas `docker compose restart`, podrás constatar que los registros siguen estando allí gracias al volumen de PostgreSQL.

5. **Disparar el Análisis Inteligente (IA)**:
   Regresa al Dashboard. En la sección **"Análisis Inteligente"**, verás una tarjeta oscura con un borde violeta degradado y el logotipo de "IA · Groq". 
   - Presiona **"Generar análisis de demanda"**.
   - Verás un estado de carga animado (*"Analizando..."*).
   - En segundos, se renderizará el texto recibido de Groq con la distribución de pasajeros por hora y recomendaciones específicas en español.

---

## 🧪 Plan y Ejecución de Pruebas Unitarias (FastAPI)

Para garantizar la estabilidad y robustez del microservicio `trip-log-service`, se diseñó y ejecutó una completa suite de pruebas unitarias e integradas sobre una base de datos real local **PostgreSQL** (`smartbus_test`).

### ⚙️ Arquitectura de la Suite de Pruebas
1. **Entorno de Datos Real**: Se optó por utilizar una base de datos PostgreSQL real local en lugar de SQLite, debido al uso de características nativas de PostgreSQL en el esquema.
2. **Ciclo de Vida de Base de Datos (`tests/conftest.py`)**:
   - Inicialización asíncrona de esquemas con `Base.metadata.create_all` ejecutado mediante `conn.run_sync` dentro del fixture de sesión `setup_test_db`.
   - Limpieza garantizada de tablas entre pruebas ejecutando `TRUNCATE TABLE trips CASCADE` al inicio y fin de cada caso de prueba, evitando interferencias de estados.
   - Sincronización del Event Loop de `pytest-asyncio` a nivel de `session` en `pytest.ini` para evitar errores de mismatch de loops.
3. **Mapeo de Pruebas**:
   - **Pruebas de Base de Datos (`tests/test_database.py`)**: Valida inserción, lecturas con filtros avanzados de fechas/rutas y cálculos estadísticos de ocupación (tanto con base de datos vacía como poblada).
   - **Pruebas de Servicio de IA (`tests/test_ai_analysis.py`)**: Aisla el microservicio de llamadas de red simulando respuestas exitosas y de fallo de Groq API mediante el mock de `httpx.AsyncClient.post`.
   - **Pruebas de API y Rutas (`tests/test_trips_router.py`)**: Realiza llamadas E2E simuladas a los endpoints HTTP usando `httpx.ASGITransport` sobre la app de FastAPI, inyectando la sesión de base de datos aislada y omitiendo la validación JWT con mocks de autenticación.

### 📊 Reporte de Ejecución de Pruebas
La ejecución local de la suite de pruebas arrojó un resultado impecable con **100% de aprobación (11/11 tests exitosos)**:

```bash
$ .\trip-log-service\venv\Scripts\python -m pytest .\trip-log-service\tests\ -v
============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\Admin\OneDrive\Escritorio\SmartBus-Unillanos\trip-log-service
configfile: pytest.ini
plugins: anyio-4.13.0, asyncio-1.3.0
asyncio: mode=Mode.AUTO, asyncio_default_fixture_loop_scope=session, asyncio_default_test_loop_scope=session
collected 11 items

trip-log-service\tests\test_ai_analysis.py::test_analyze_demand_success PASSED [  9%]
trip-log-service\tests\test_ai_analysis.py::test_analyze_demand_empty_trips PASSED [ 18%]
trip-log-service\tests\test_database.py::test_save_and_retrieve_trip PASSED [ 27%]
trip-log-service\tests\test_database.py::test_get_all_trips_filtering PASSED [ 36%]
trip-log-service\tests\test_database.py::test_compute_stats_empty PASSED [ 45%]
trip-log-service\tests\test_database.py::test_compute_stats_populated PASSED [ 54%]
trip-log-service\tests\test_trips_router.py::test_create_and_list_trips PASSED [ 63%]
trip-log-service\tests\test_trips_router.py::test_get_trip_stats_summary PASSED [ 72%]
trip-log-service\tests\test_demand_analysis_success PASSED [ 81%]
trip-log-service\tests\test_demand_analysis_no_data PASSED [ 90%]
trip-log-service\tests\test_demand_analysis_ai_gateway_error PASSED [100%]

============================= 11 passed in 4.44s ==============================
```
