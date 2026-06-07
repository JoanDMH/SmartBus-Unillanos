"""DEV-B1 — Entrenamiento del modelo Prophet con regresores exógenos.

Estrategia:
  - Modelo base: Prophet captura estacionalidad diaria + semanal del campus.
  - Regresores adicionales: academic_week, special_event, weather_lluvioso,
    is_peak (hora pico) mejoran la predicción ante eventos exógenos.
  - Validación cruzada temporal con horizon=7 días y period=3 días.
  - Artefacto: model_prophet.pkl guardado localmente y subido a Azure Blob.

Uso:
  python train_prophet.py [--route PARQUE]
"""

import argparse
import os
import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics
from sklearn.metrics import mean_absolute_error

from db_loader import load_trips
from upload import upload_artifact

ARTIFACT_NAME = "model_prophet.pkl"
MLFLOW_EXPERIMENT = "smartbus-demand-prophet"


def build_prophet_regressors(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega columnas requeridas por Prophet como regresores."""
    return df[["ds", "y", "academic_week", "special_event",
               "weather_lluvioso", "is_peak"]].copy()


def train(route_id: str = "PARQUE") -> None:
    mlflow.set_experiment(MLFLOW_EXPERIMENT)

    df = load_trips(route_id=route_id)
    if len(df) < 30:
        print(f"[Prophet] Datos insuficientes ({len(df)} registros). Mínimo: 30. Abortando.")
        return

    df_train = build_prophet_regressors(df)
    # Convertir bool a int para Prophet
    df_train["special_event"] = df_train["special_event"].astype(int)
    df_train["is_peak"]       = df_train["is_peak"].astype(int)

    # --- Modelo ---
    model = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=True,
        daily_seasonality=True,
        seasonality_mode="multiplicative",
        changepoint_prior_scale=0.05,   # regularización conservadora (dataset pequeño)
    )
    model.add_regressor("academic_week")
    model.add_regressor("special_event")
    model.add_regressor("weather_lluvioso")
    model.add_regressor("is_peak")

    with mlflow.start_run(run_name=f"prophet_{route_id}"):
        mlflow.log_params({
            "route_id": route_id,
            "n_records": len(df_train),
            "changepoint_prior_scale": 0.05,
            "seasonality_mode": "multiplicative",
        })

        model.fit(df_train)

        # --- Validación cruzada temporal ---
        try:
            # Calcular el rango real de fechas (días únicos, no registros).
            # Usar len(df) causaría initial="200 days" con solo 60 días reales → crash.
            date_span_days = (df_train["ds"].max() - df_train["ds"].min()).days
            initial_days   = max(14, date_span_days // 2)
            df_cv = cross_validation(
                model,
                initial=f"{initial_days} days",
                period="3 days",
                horizon="7 days",
                parallel=None,
            )
            perf = performance_metrics(df_cv)
            mae  = perf["mae"].mean()
            rmse = perf["rmse"].mean()
            mlflow.log_metrics({"val_mae": mae, "val_rmse": rmse})
            print(f"[Prophet] CV — MAE: {mae:.2f} | RMSE: {rmse:.2f}")
            if mae > 5:
                print(f"[Prophet] AVISO: MAE={mae:.2f} supera el umbral de 5 pasajeros.")
        except Exception as e:
            print(f"[Prophet] CV omitida (datos insuficientes): {e}")

        # --- Guardar artefacto ---
        os.makedirs("/tmp/smartbus_models", exist_ok=True)
        local_path = f"/tmp/smartbus_models/{ARTIFACT_NAME}"
        joblib.dump(model, local_path)
        mlflow.log_artifact(local_path, artifact_path="models")
        print(f"[Prophet] Artefacto guardado en {local_path}")

        # --- Subir a Azure Blob ---
        upload_artifact(local_path, ARTIFACT_NAME)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--route", default="PARQUE", help="route_id a entrenar")
    args = parser.parse_args()
    train(route_id=args.route)
