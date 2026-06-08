"""Servicio de predicción de demanda — lógica reutilizable sin capa HTTP.

Extraído de predict_router.py para permitir llamadas directas desde
optimization_router.py sin pasar por loopback HTTP (que requeriría JWT
y añadiría latencia + riesgo de fallo en contenedor).

Importar desde aquí, NO hacer petición HTTP interna a /trips/ai/predict-demand.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List

import numpy as np

from services.model_loader import get_model, models_available

logger = logging.getLogger(__name__)

PEAK_HOURS = {6, 7, 8, 12, 13, 17, 18}
WEATHER_DEFAULTS = {"weather_soleado": 0, "weather_nublado": 1, "weather_lluvioso": 0}


def _prophet_predict(
    model,
    ds_list: List[datetime],
    academic_week: int,
    special_event: bool,
) -> List[dict]:
    import pandas as pd

    future = pd.DataFrame({
        "ds": ds_list,
        "academic_week": academic_week,
        "special_event": int(special_event),
        "weather_lluvioso": 0,
        "is_peak": [1 if d.hour in PEAK_HOURS else 0 for d in ds_list],
    })
    forecast = model.predict(future)
    results = []
    for _, row in forecast.iterrows():
        yhat = max(0, round(float(row["yhat"])))
        yhat_low = max(0, round(float(row.get("yhat_lower", yhat * 0.85))))
        yhat_high = min(100, round(float(row.get("yhat_upper", yhat * 1.15))))
        results.append({
            "hour": row["ds"].hour,
            "predicted_passengers": yhat,
            "confidence_low": yhat_low,
            "confidence_high": yhat_high,
        })
    return results


def _xgboost_predict(
    artifact: dict,
    ds_list: List[datetime],
    academic_week: int,
    special_event: bool,
) -> List[dict]:
    import pandas as pd

    model = artifact["model"]
    feature_cols = artifact["feature_cols"]

    rows = []
    for ds in ds_list:
        row = {
            "hour": ds.hour,
            "day_of_week": ds.weekday(),
            "academic_week": academic_week,
            "special_event": int(special_event),
            "is_peak": int(ds.hour in PEAK_HOURS),
            **WEATHER_DEFAULTS,
            "lag_1h": 30,
            "lag_24h": 35,
            "lag_168h": 35,
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
            "hour": ds.hour,
            "predicted_passengers": yhat,
            "confidence_low": max(0, yhat - margin),
            "confidence_high": min(100, yhat + margin),
        })
    return results


def predict_for_date(
    date: str,
    academic_week: int = 1,
    special_event: bool = False,
    model_name: str = "best",
    hours: List[int] | None = None,
) -> dict | None:
    """Predice demanda para una fecha dada. Devuelve None si no hay modelos.

    Args:
        date: Fecha en formato YYYY-MM-DD.
        academic_week: Semana académica (1-18).
        special_event: Si hay evento especial ese día.
        model_name: 'prophet', 'xgboost' o 'best'.
        hours: Lista de horas a predecir. Si None, predice las 24h.

    Returns:
        Dict con 'model_used', 'predictions' [{hour, predicted_passengers, ...}]
        o None si no hay modelos disponibles.
    """
    available = models_available()
    if not available:
        logger.warning("[PredictionService] Sin modelos disponibles — no se puede predecir.")
        return None

    if model_name == "best":
        chosen_key = "model_xgboost" if "model_xgboost" in available else available[0]
    elif f"model_{model_name}" in available:
        chosen_key = f"model_{model_name}"
    else:
        logger.warning(f"[PredictionService] Modelo '{model_name}' no disponible.")
        return None

    try:
        base_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        logger.error(f"[PredictionService] Fecha inválida: {date}")
        return None

    hours_to_predict = hours if hours is not None else list(range(24))
    ds_list = [base_date.replace(hour=h) for h in hours_to_predict]

    artifact = get_model(chosen_key)
    if chosen_key == "model_prophet":
        predictions = _prophet_predict(artifact, ds_list, academic_week, special_event)
    else:
        predictions = _xgboost_predict(artifact, ds_list, academic_week, special_event)

    return {
        "model_used": chosen_key,
        "route_id": "PARQUE",
        "date": date,
        "predictions": predictions,
    }
