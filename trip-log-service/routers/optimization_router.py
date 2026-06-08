"""DEV-C3 — Endpoints del itinerario semanal optimizado.

Actúa como orquestador entre:
  1. El endpoint de predicción (/trips/ai/predict-demand) para obtener la demanda.
  2. El optimization-service (PuLP) para resolver la grilla óptima.
  3. La tabla `schedules` en PostgreSQL para persistir y recuperar itinerarios.

Endpoints:
  POST /trips/optimization/weekly-schedule
    Genera y persiste un nuevo itinerario para la semana indicada.
    Requiere rol `dispatcher` o `admin`.

  POST /trips/optimization/weekly-schedule/approve
    Aprueba el último itinerario pendiente (human-in-the-loop).
    Requiere rol `dispatcher` o `admin`.

  GET /trips/optimization/weekly-schedule/latest
    Devuelve el último itinerario aprobado, consumible por el frontend.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt_validator import get_current_user
from config import OPTIMIZATION_SERVICE_URL
from services.prediction_service import predict_for_date
from storage.database import ScheduleRow, get_session

router = APIRouter()

# ── Schemas de request/response ───────────────────────────────────────────────

class FleetConfigIn(BaseModel):
    available_buses: int = 3
    bus_type: str = "estandar"
    available_drivers: int = 6


class GenerateScheduleRequest(BaseModel):
    week_label: str             # e.g. "2026-W24"
    academic_week: int = 1
    special_event: bool = False
    fleet: Optional[FleetConfigIn] = None


class ApproveScheduleRequest(BaseModel):
    schedule_id: str            # UUID del itinerario a aprobar


# ── Helpers ───────────────────────────────────────────────────────────────────

WEEKDAYS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado"]

WEEKDAY_ISO = {
    "lunes": 0, "martes": 1, "miercoles": 2,
    "jueves": 3, "viernes": 4, "sabado": 5,
}


def _schedule_row_to_dict(row: ScheduleRow) -> dict:
    return {
        "id": row.id,
        "week_label": row.week_label,
        "status": row.status,
        "schedule_by_day": row.schedule_data,
        "total_cost_cop": row.total_cost_cop,
        "fleet_config": row.fleet_config,
        "generated_by": row.generated_by,
        "approved_by": row.approved_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "approved_at": row.approved_at.isoformat() if row.approved_at else None,
    }


async def _fetch_weekly_demand(
    academic_week: int,
    special_event: bool,
    week_label: str,
) -> dict[str, dict[str, float]]:
    """Obtiene demanda predicha para las 24h × 6 días de la semana.

    Llama directamente a prediction_service.predict_for_date() — sin HTTP loopback.
    Esto evita la dependencia de JWT, latencia de red y fallos de red en Docker.
    week_label tiene formato 'YYYY-Www' (e.g. '2026-W24').
    """
    import datetime as dt
    import isoweek

    try:
        year, week_num = week_label.split("-W")
        w = isoweek.Week(int(year), int(week_num))
        week_dates = {
            day: w.day(i).strftime("%Y-%m-%d")
            for i, day in enumerate(WEEKDAYS)
        }
    except Exception:
        today = datetime.now(timezone.utc).date()
        monday = today - dt.timedelta(days=today.weekday())
        week_dates = {
            day: (monday + dt.timedelta(days=i)).strftime("%Y-%m-%d")
            for i, day in enumerate(WEEKDAYS)
        }

    weekly_demand: dict[str, dict[str, float]] = {}

    for day, date_str in week_dates.items():
        try:
            # Llamada directa al servicio Python — sin HTTP, sin JWT
            result = await run_in_threadpool(
                predict_for_date,
                date_str,
                academic_week,
                special_event,
                "best",
                None,   # todas las horas
            )
            if result:
                weekly_demand[day] = {
                    str(p["hour"]): float(p["predicted_passengers"])
                    for p in result.get("predictions", [])
                }
            else:
                weekly_demand[day] = {}
        except Exception:
            weekly_demand[day] = {}

    return weekly_demand


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/trips/optimization/weekly-schedule",
    status_code=status.HTTP_201_CREATED,
    tags=["Optimization"],
)
async def generate_weekly_schedule(
    body: GenerateScheduleRequest,
    user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Genera el itinerario semanal óptimo y lo persiste como pendiente de aprobación.

    Flujo:
    1. Obtiene demanda predicha para cada día de la semana.
    2. Envía la demanda al optimization-service (PuLP).
    3. Persiste el resultado en la tabla `schedules` con status=pending.
    4. Devuelve el itinerario para revisión humana antes de su aprobación.
    """
    # 1. Obtener demanda predicha
    try:
        weekly_demand = await _fetch_weekly_demand(
            academic_week=body.academic_week,
            special_event=body.special_event,
            week_label=body.week_label,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error obteniendo predicciones de demanda: {exc}",
        )

    # 2. Llamar al optimization-service
    opt_payload = {
        "weekly_demand": weekly_demand,
        "fleet": body.fleet.model_dump() if body.fleet else None,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{OPTIMIZATION_SERVICE_URL}/optimize/weekly-schedule",
                json=opt_payload,
            )
        resp.raise_for_status()
        opt_result = resp.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"optimization-service no disponible en {OPTIMIZATION_SERVICE_URL}. "
                   "Verifica que el contenedor esté corriendo.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error en optimization-service: {exc}",
        )

    # 3. Persistir en tabla schedules
    row = ScheduleRow(
        id=str(uuid.uuid4()),
        week_label=body.week_label,
        status="pending",
        schedule_data=opt_result.get("schedule_by_day", {}),
        total_cost_cop=int(opt_result.get("total_cost_cop", 0)),
        fleet_config=body.fleet.model_dump() if body.fleet else None,
        generated_by=f"optimizer:{user}",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    return {
        **_schedule_row_to_dict(row),
        "optimizer_status": opt_result.get("status"),
        "solver_message": opt_result.get("solver_message"),
    }


@router.post(
    "/trips/optimization/weekly-schedule/approve",
    tags=["Optimization"],
)
async def approve_weekly_schedule(
    body: ApproveScheduleRequest,
    user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Aprueba un itinerario pendiente (human-in-the-loop).

    Cambia el status de `pending` a `approved` y registra quién aprobó y cuándo.
    Solo se puede aprobar un itinerario a la vez por semana.
    """
    stmt = select(ScheduleRow).where(ScheduleRow.id == body.schedule_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Itinerario {body.schedule_id} no encontrado.",
        )

    if row.status == "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este itinerario ya fue aprobado.",
        )

    row.status = "approved"
    row.approved_by = user
    row.approved_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(row)

    return _schedule_row_to_dict(row)


@router.get(
    "/trips/optimization/weekly-schedule/latest",
    tags=["Optimization"],
)
async def get_latest_approved_schedule(
    week_label: Optional[str] = Query(None, description="Filtrar por semana (e.g. '2026-W24'). Si se omite, devuelve el más reciente."),
    user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Devuelve el último itinerario aprobado.

    Consumido por el frontend del despachador (ScheduleApprovalPage)
    y por el sistema de visualización de grillas.
    """
    stmt = (
        select(ScheduleRow)
        .where(ScheduleRow.status == "approved")
        .order_by(ScheduleRow.approved_at.desc())
    )
    if week_label:
        stmt = stmt.where(ScheduleRow.week_label == week_label)

    result = await session.execute(stmt)
    row = result.scalars().first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay itinerarios aprobados"
            + (f" para la semana {week_label}." if week_label else "."),
        )

    return _schedule_row_to_dict(row)


@router.get(
    "/trips/optimization/weekly-schedule",
    tags=["Optimization"],
)
async def list_schedules(
    status_filter: Optional[str] = Query(None, alias="status", pattern="^(pending|approved)$"),
    user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Lista todos los itinerarios, opcionalmente filtrados por status."""
    stmt = select(ScheduleRow).order_by(ScheduleRow.created_at.desc())
    if status_filter:
        stmt = stmt.where(ScheduleRow.status == status_filter)

    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [_schedule_row_to_dict(r) for r in rows]
