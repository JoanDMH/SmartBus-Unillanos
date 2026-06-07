"""DEV-B2 — Entrenamiento del modelo XGBoost (ensamble complementario a Prophet).

Estrategia:
  - Features tabulares derivadas de la serie de tiempo: lag_1h, lag_24h,
    lag_168h (semana anterior), rolling_mean_7d, más variables de contexto.
  - Validación: TimeSeriesSplit (5 folds) para respetar la naturaleza temporal.
  - El artefacto .pkl se evalúa contra holdout_dataset.csv en CI/CD (DEV-E1).

Uso:
  python train_xgboost.py [--route PARQUE]
"""

import argparse
import os
import joblib
import mlflow
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

from db_loader import load_trips
from upload import upload_artifact

ARTIFACT_NAME = "model_xgboost.pkl"
MLFLOW_EXPERIMENT = "smartbus-demand-xgboost"

FEATURE_COLS = [
    "hour", "day_of_week", "academic_week", "special_event",
    "is_peak", "weather_soleado", "weather_nublado", "weather_lluvioso",
    "lag_1h", "lag_24h", "lag_168h", "rolling_mean_24h",
]


def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """Añade features de lag y media móvil ordenando por tiempo."""
    df = df.sort_values("ds").copy()
    df["lag_1h"]          = df["y"].shift(1)
    df["lag_24h"]         = df["y"].shift(24)
    df["lag_168h"]        = df["y"].shift(168)   # misma hora, semana anterior
    # shift(1) antes del rolling evita data leakage:
    # rolling_mean_24h en t usa y[t-24]…y[t-1], nunca y[t].
    df["rolling_mean_24h"] = df["y"].shift(1).rolling(24, min_periods=1).mean()
    df["special_event"]   = df["special_event"].astype(int)
    df["is_peak"]         = df["is_peak"].astype(int)
    return df.dropna(subset=["lag_1h"])            # elimina primeras filas sin lag


def train(route_id: str = "PARQUE") -> None:
    mlflow.set_experiment(MLFLOW_EXPERIMENT)

    df = load_trips(route_id=route_id)
    if len(df) < 50:
        print(f"[XGBoost] Datos insuficientes ({len(df)} registros). Mínimo: 50. Abortando.")
        return

    df = add_lag_features(df)
    X = df[FEATURE_COLS].values
    y = df["y"].values

    params = {
        "n_estimators":     300,
        "max_depth":        4,
        "learning_rate":    0.05,
        "subsample":        0.8,
        "colsample_bytree": 0.8,
        "reg_alpha":        0.1,    # L1 — regularización para dataset pequeño
        "reg_lambda":       1.0,    # L2
        "random_state":     42,
        "n_jobs":           -1,
    }

    with mlflow.start_run(run_name=f"xgboost_{route_id}"):
        mlflow.log_params({"route_id": route_id, "n_records": len(df), **params})

        # --- Validación cruzada temporal ---
        tscv = TimeSeriesSplit(n_splits=5)
        mae_scores, rmse_scores = [], []

        for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
            model = XGBRegressor(**params)
            model.fit(X[train_idx], y[train_idx],
                      eval_set=[(X[val_idx], y[val_idx])],
                      verbose=False)
            preds = model.predict(X[val_idx])
            preds = np.clip(preds, 0, 100)   # pasajeros no pueden ser negativos ni > 100
            mae_scores.append(mean_absolute_error(y[val_idx], preds))
            rmse_scores.append(mean_squared_error(y[val_idx], preds) ** 0.5)

        mean_mae  = float(np.mean(mae_scores))
        mean_rmse = float(np.mean(rmse_scores))
        mlflow.log_metrics({"val_mae": mean_mae, "val_rmse": mean_rmse})
        print(f"[XGBoost] CV (5-fold) — MAE: {mean_mae:.2f} | RMSE: {mean_rmse:.2f}")

        if mean_mae > 5:
            print(f"[XGBoost] AVISO: MAE={mean_mae:.2f} supera el umbral de 5 pasajeros.")

        # --- Entrenar modelo final sobre todos los datos ---
        final_model = XGBRegressor(**params)
        final_model.fit(X, y)

        # --- Feature importance ---
        importance = dict(zip(FEATURE_COLS, final_model.feature_importances_))
        top = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
        print("[XGBoost] Top-5 features:", top)
        mlflow.log_dict(importance, "feature_importance.json")

        # --- Guardar artefacto ---
        os.makedirs("/tmp/smartbus_models", exist_ok=True)
        local_path = f"/tmp/smartbus_models/{ARTIFACT_NAME}"
        # Guardamos también los nombres de features para validación en CI
        artifact = {"model": final_model, "feature_cols": FEATURE_COLS}
        joblib.dump(artifact, local_path)
        mlflow.log_artifact(local_path, artifact_path="models")
        print(f"[XGBoost] Artefacto guardado en {local_path}")

        # --- Subir a Azure Blob ---
        upload_artifact(local_path, ARTIFACT_NAME)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--route", default="PARQUE", help="route_id a entrenar")
    args = parser.parse_args()
    train(route_id=args.route)
