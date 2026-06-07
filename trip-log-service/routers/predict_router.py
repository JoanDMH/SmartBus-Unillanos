"""DEV-B4 — Endpoint de inferencia de demanda de pasajeros.

GET /trips/ai/predict-demand
  Parámetros query:
    date  (YYYY-MM-DD, requerido) — fecha para la que se predice
    hour  (0-23, opcional)        — si se omite, devuelve predicciones para todas las horas del día
    model (prophet|xgboost|best)  — modelo a usar (default: best)

Respuesta JSON:
  {
    "model_used": "model_xgboost",
    "route_id":   "PARQUE",
    "predictions": [
      {"hour": 6, "predicted_passengers": 52, "confidence_low": 44, "confidence_high": 60},
      ...
    ]
  }
"""

from datetime import datetime

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth.jwt_validator import get_current_user
from services.model_loader import get_model, models_available

router = APIRouter()

PEAK_HOURS = {6, 7, 8, 12, 13, 17, 18}
WEATHER_DEFAULTS = {"weather_soleado": 0, "weather_nublado": 1, "weather_lluvioso": 0}


def _prophet_predict(model, ds_list: list[datetime], academic_week: int, special_event: bool) -> list[dict]:
    import pandas as pd
    future = pd.DataFrame({
        "ds":              ds_list,
        "academic_week":   academic_week,
        "special_event":   int(special_event),
        "weather_lluvioso": 0,          # default conservador
        "is_peak":         [1 if d.hour in PEAK_HOURS else 0 for d in ds_list],
    })
    forecast = model.predict(future)
    results = []
    for _, row in forecast.iterrows():
        yhat     = max(0, round(float(row["yhat"])))
        yhat_low = max(0, round(float(row.get("yhat_lower", yhat * 0.85))))
        yhat_high = min(100, round(float(row.get("yhat_upper", yhat * 1.15))))
        results.append({
            "hour":                 row["ds"].hour,
            "predicted_passengers": yhat,
            "confidence_low":       yhat_low,
            "confidence_high":      yhat_high,
        })
    return results


def _xgboost_predict(artifact: dict, ds_list: list[datetime], academic_week: int, special_event: bool) -> list[dict]:
    import pandas as pd
    model       = artifact["model"]
    feature_cols = artifact["feature_cols"]

    rows = []
    for ds in ds_list:
        row = {
            "hour":            ds.hour,
            "day_of_week":     ds.weekday(),
            "academic_week":   academic_week,
            "special_event":   int(special_event),
            "is_peak":         int(ds.hour in PEAK_HOURS),
            **WEATHER_DEFAULTS,
            # Lags no disponibles en inferencia online → usar media histórica como proxy
            "lag_1h":          30,
            "lag_24h":         35,
            "lag_168h":        35,
            "rolling_mean_24h": 32,
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0

    preds = np.clip(model.predict(df[feature_cols].values), 0, 100)
    results = []
    for i, ds in enumerate(ds_list):
        yhat = round(float(preds[i]))
        margin = max(3, round(yhat * 0.12))
        results.append({
            "hour":                 ds.hour,
            "predicted_passengers": yhat,
            "confidence_low":       max(0, yhat - margin),
            "confidence_high":      min(100, yhat + margin),
        })
    return results


@router.get("/trips/ai/predict-demand", tags=["AI"])
async def predict_demand(
    date:          str  = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Fecha de predicción (YYYY-MM-DD)"),
    hour:          int  | None = Query(None, ge=0, le=23, description="Hora específica (0-23). Si se omite, devuelve las 24 horas."),
    academic_week: int  = Query(1, ge=1, le=18, description="Semana académica actual"),
    special_event: bool = Query(False, description="¿Hay evento especial ese día?"),
    model_name:    str  = Query("best", pattern="^(prophet|xgboost|best)$", description="Modelo a usar"),
    user: str = Depends(get_current_user),
):
    """Predice la demanda de pasajeros para una fecha y hora dadas."""
    available = models_available()
    if not available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ningún modelo de predicción está disponible. Ejecuta el pipeline de entrenamiento primero.",
        )

    # Resolver qué modelo usar
    chosen_key: str
    if model_name == "best":
        chosen_key = "model_xgboost" if "model_xgboost" in available else available[0]
    elif f"model_{model_name}" in available:
        chosen_key = f"model_{model_name}"
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Modelo '{model_name}' no disponible. Disponibles: {available}",
        )

    # Construir lista de datetimes a predecir
    try:
        base_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Fecha inválida.")

    hours_to_predict = [hour] if hour is not None else list(range(24))
    ds_list = [base_date.replace(hour=h) for h in hours_to_predict]

    # Inferencia
    artifact = get_model(chosen_key)
    if chosen_key == "model_prophet":
        predictions = _prophet_predict(artifact, ds_list, academic_week, special_event)
    else:
        predictions = _xgboost_predict(artifact, ds_list, academic_week, special_event)

    return {
        "model_used":  chosen_key,
        "route_id":    "PARQUE",
        "date":        date,
        "predictions": predictions,
    }
