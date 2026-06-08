"""SmartBus Unillanos — optimization-service entry point.

Microservicio independiente que expone el motor PuLP como API REST.
Corre en el puerto 8001 (configurable vía PORT env var).

Endpoints:
  POST /optimize/weekly-schedule  — resuelve la optimización semanal
  GET  /                          — health check
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional
import os

from optimizer import solve_weekly_schedule, WeeklyScheduleResult
from constraints import FleetConfig

app = FastAPI(
    title="SmartBus optimization-service",
    description="Motor de programación lineal entera (PuLP) para optimización de frecuencias — Ruta Parque Unillanos",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ──────────────────────────────────────────────────────────────────

class FleetConfigRequest(BaseModel):
    available_buses: int = 3
    bus_type: str = "estandar"
    available_drivers: int = 6
    operating_hours: Optional[list[int]] = None


class WeeklyOptimizationRequest(BaseModel):
    weekly_demand: Dict[str, Dict[str, float]]  # {dia: {hora_str: pasajeros}}
    fleet: Optional[FleetConfigRequest] = None


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/", tags=["health"])
async def health():
    return {"status": "ok", "service": "optimization-service"}


@app.post("/optimize/weekly-schedule", tags=["optimization"])
async def optimize_weekly_schedule(body: WeeklyOptimizationRequest):
    """Resuelve la optimización semanal de frecuencias con PuLP.

    Recibe la demanda predicha por día y hora, y devuelve el número óptimo
    de buses a despachar en cada franja horaria minimizando costos operativos.
    """
    # Convertir claves de hora de str a int (JSON serializa keys como strings)
    weekly_demand_int: Dict[str, Dict[int, float]] = {
        day: {int(h): float(v) for h, v in hours.items()}
        for day, hours in body.weekly_demand.items()
    }

    # Construir FleetConfig
    if body.fleet:
        fleet = FleetConfig(
            available_buses=body.fleet.available_buses,
            bus_type=body.fleet.bus_type,
            available_drivers=body.fleet.available_drivers,
            operating_hours=body.fleet.operating_hours or list(range(5, 22)),
        )
    else:
        fleet = FleetConfig()

    result: WeeklyScheduleResult = solve_weekly_schedule(
        weekly_demand=weekly_demand_int,
        fleet=fleet,
    )

    # Serializar resultado
    schedule_json = {}
    for day, hourly_list in result.schedule_by_day.items():
        schedule_json[day] = [
            {
                "hour": h.hour,
                "buses_dispatched": h.buses_dispatched,
                "demand_forecast": h.demand_forecast,
                "passengers_covered": h.passengers_covered,
                "cost_cop": round(h.cost_cop),
            }
            for h in hourly_list
        ]

    return {
        "status": result.status,
        "is_optimal": result.is_optimal,
        "total_cost_cop": round(result.total_cost_cop),
        "schedule_by_day": schedule_json,
        "solver_message": result.solver_message,
    }
