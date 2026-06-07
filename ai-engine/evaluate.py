"""DEV-B3 / DEV-E1 — Evaluación de artefactos contra el holdout dataset.

Usado en dos contextos:
  1. CI/CD (GitHub Actions): valida que MAE ≤ 5 antes de promover a producción.
  2. Manual: comparar versiones de modelos localmente.

Salida:
  - Exit code 0 → modelo aprobado (MAE ≤ umbral)
  - Exit code 1 → modelo rechazado (bloquea el merge en CI)

Uso:
  python evaluate.py --model prophet   # evalúa model_prophet.pkl
  python evaluate.py --model xgboost  # evalúa model_xgboost.pkl
  python evaluate.py --model all      # evalúa ambos y reporta el mejor
"""

import argparse
import os
import sys
import joblib
import mlflow
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

MAE_THRESHOLD    = 5.0   # umbral contractual: ≤ 5 pasajeros
HOLDOUT_PATH     = os.path.join(os.path.dirname(__file__), "holdout_dataset.csv")
MODEL_CACHE_PATH = "/tmp/smartbus_models"
MLFLOW_EXPERIMENT = "smartbus-ci-evaluation"


def load_holdout() -> pd.DataFrame:
    if not os.path.exists(HOLDOUT_PATH):
        print(f"[Evaluate] ERROR: holdout dataset no encontrado en {HOLDOUT_PATH}")
        sys.exit(1)
    df = pd.read_csv(HOLDOUT_PATH, parse_dates=["ds"])
    df["is_peak"]       = df["hour"].isin([6, 7, 8, 12, 13, 17, 18]).astype(int)
    df["special_event"] = df["special_event"].astype(int)
    return df


def evaluate_prophet(df: pd.DataFrame) -> float:
    model_path = os.path.join(MODEL_CACHE_PATH, "model_prophet.pkl")
    if not os.path.exists(model_path):
        print("[Evaluate] model_prophet.pkl no encontrado. Omitiendo.")
        return float("inf")

    model = joblib.load(model_path)
    future = df[["ds", "academic_week", "special_event",
                 "weather_lluvioso", "is_peak"]].copy()
    forecast = model.predict(future)
    preds = np.clip(forecast["yhat"].values, 0, 100)
    mae   = mean_absolute_error(df["y"].values, preds)
    rmse  = mean_squared_error(df["y"].values, preds) ** 0.5
    print(f"[Prophet]  Holdout MAE={mae:.2f} | RMSE={rmse:.2f}")
    return mae


def evaluate_xgboost(df: pd.DataFrame) -> float:
    model_path = os.path.join(MODEL_CACHE_PATH, "model_xgboost.pkl")
    if not os.path.exists(model_path):
        print("[Evaluate] model_xgboost.pkl no encontrado. Omitiendo.")
        return float("inf")

    artifact = joblib.load(model_path)
    model, feature_cols = artifact["model"], artifact["feature_cols"]

    # Asegurar que el holdout tiene todas las features necesarias
    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0

    X    = df[feature_cols].values
    preds = np.clip(model.predict(X), 0, 100)
    mae   = mean_absolute_error(df["y"].values, preds)
    rmse  = mean_squared_error(df["y"].values, preds) ** 0.5
    print(f"[XGBoost]  Holdout MAE={mae:.2f} | RMSE={rmse:.2f}")
    return mae


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["prophet", "xgboost", "all"], default="all")
    args = parser.parse_args()

    mlflow.set_experiment(MLFLOW_EXPERIMENT)
    df = load_holdout()
    print(f"[Evaluate] Holdout: {len(df)} registros")

    results: dict[str, float] = {}

    with mlflow.start_run(run_name=f"ci_eval_{args.model}"):
        if args.model in ("prophet", "all"):
            results["prophet"] = evaluate_prophet(df)
            mlflow.log_metric("holdout_mae_prophet", results["prophet"])

        if args.model in ("xgboost", "all"):
            results["xgboost"] = evaluate_xgboost(df)
            mlflow.log_metric("holdout_mae_xgboost", results["xgboost"])

        best_mae   = min(results.values())
        best_model = min(results, key=results.get)
        mlflow.log_metric("best_mae", best_mae)
        mlflow.log_param("best_model", best_model)

    print(f"\n[Evaluate] Mejor modelo: {best_model} (MAE={best_mae:.2f})")
    print(f"[Evaluate] Umbral: {MAE_THRESHOLD} pasajeros")

    if best_mae <= MAE_THRESHOLD:
        print(f"[Evaluate] APROBADO — El modelo puede promoverse a produccion.")
        sys.exit(0)
    else:
        print(f"[Evaluate] RECHAZADO — MAE={best_mae:.2f} supera el umbral={MAE_THRESHOLD}.")
        sys.exit(1)


if __name__ == "__main__":
    main()
