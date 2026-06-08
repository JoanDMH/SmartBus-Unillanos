"""DEV-B4 — Endpoint de inferencia de demanda de pasajeros.

GET /trips/ai/predict-demand
  Parámetros query:
    date  (YYYY-MM-DD, requerido) — fecha para la que se predice
    hour  (0-23, opcional)        — si se omite, devuelve predicciones para todas las horas del día
    model (prophet|xgboost|best)  — modelo a usar (default: best)

La lógica de inferencia vive en services/prediction_service.py para
permitir llamadas directas (sin HTTP) desde optimization_router.py.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool

from auth.jwt_validator import get_current_user
from services.model_loader import models_available
from services.prediction_service import predict_for_date

router = APIRouter()


@router.get("/trips/ai/predict-demand", tags=["AI"])
async def predict_demand(
    date:          str       = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Fecha de predicción (YYYY-MM-DD)"),
    hour:          int | None = Query(None, ge=0, le=23, description="Hora específica (0-23). Si se omite, devuelve las 24 horas."),
    academic_week: int       = Query(1, ge=1, le=18, description="Semana académica actual"),
    special_event: bool      = Query(False, description="¿Hay evento especial ese día?"),
    model_name:    str       = Query("best", pattern="^(prophet|xgboost|best)$", description="Modelo a usar"),
    user: str = Depends(get_current_user),
):
    """Predice la demanda de pasajeros para una fecha y hora dadas.

    La inferencia corre en un thread pool para no bloquear el event loop
    de FastAPI durante el procesamiento CPU-bound de pandas/numpy.
    """
    if not models_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ningún modelo de predicción está disponible. Ejecuta el pipeline de entrenamiento primero.",
        )

    hours_param = [hour] if hour is not None else None

    # run_in_threadpool delega el trabajo CPU-bound a un hilo separado,
    # liberando el event loop para servir otras peticiones concurrentes.
    result = await run_in_threadpool(
        predict_for_date,
        date,
        academic_week,
        special_event,
        model_name,
        hours_param,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Modelo '{model_name}' no disponible.",
        )

    return result
