"""SmartBus Unillanos — trip-log-service entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.routes_router import router as routes_router
from routers.trips_router import router as trips_router
from routers.predict_router import router as predict_router
from storage.database import init_db
from services.model_loader import load_all_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create database tables and load ML models into memory."""
    await init_db()
    load_all_models()   # DEV-B4 — carga Prophet / XGBoost desde Azure Blob o caché local
    yield


app = FastAPI(
    title="SmartBus trip-log-service",
    description="Microservicio de registro de viajes para Ruta Parque — MVP SmartBus Unillanos",
    version="0.3.0",
    lifespan=lifespan,
)

# Allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_router)
app.include_router(trips_router)
app.include_router(predict_router)


@app.get("/", tags=["health"])
async def health():
    """Health-check endpoint."""
    return {"status": "ok", "service": "trip-log-service"}
