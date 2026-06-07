"""DEV-B4 — Carga del artefacto de ML desde Azure Blob Storage o caché local.

El modelo se carga UNA SOLA VEZ en el lifespan de FastAPI y se almacena
en memoria. Si Azure Blob no está configurado, se intenta cargar desde
la ruta local MODEL_LOCAL_CACHE_PATH (útil en desarrollo).

Modelos soportados:
  - model_prophet.pkl  → objeto Prophet
  - model_xgboost.pkl  → dict {"model": XGBRegressor, "feature_cols": list[str]}
"""

import os
import logging
import joblib

from config import (
    AZURE_STORAGE_CONNECTION_STRING,
    AZURE_MODEL_CONTAINER,
    MODEL_LOCAL_CACHE_PATH,
)

logger = logging.getLogger(__name__)

# Cache en memoria — populado en lifespan de FastAPI
_models: dict = {}

SUPPORTED_MODELS = ["model_prophet.pkl", "model_xgboost.pkl"]


def _download_from_blob(blob_name: str, local_path: str) -> bool:
    """Descarga un artefacto de Azure Blob. Devuelve True si tuvo éxito."""
    if not AZURE_STORAGE_CONNECTION_STRING:
        return False
    try:
        from azure.storage.blob import BlobServiceClient
        client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        blob = client.get_blob_client(container=AZURE_MODEL_CONTAINER, blob=blob_name)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(blob.download_blob().readall())
        logger.info(f"[ModelLoader] {blob_name} descargado de Azure Blob.")
        return True
    except Exception as e:
        logger.warning(f"[ModelLoader] No se pudo descargar {blob_name} de Azure: {e}")
        return False


def load_all_models() -> None:
    """Carga todos los modelos disponibles en el cache de memoria."""
    os.makedirs(MODEL_LOCAL_CACHE_PATH, exist_ok=True)

    for blob_name in SUPPORTED_MODELS:
        local_path = os.path.join(MODEL_LOCAL_CACHE_PATH, blob_name)
        key = blob_name.replace(".pkl", "")

        # 1. Intentar descargar de Azure si no existe localmente
        if not os.path.exists(local_path):
            _download_from_blob(blob_name, local_path)

        # 2. Cargar desde disco
        if os.path.exists(local_path):
            try:
                _models[key] = joblib.load(local_path)
                logger.info(f"[ModelLoader] {key} cargado en memoria.")
            except Exception as e:
                logger.error(f"[ModelLoader] Error cargando {key}: {e}")
        else:
            logger.warning(f"[ModelLoader] {blob_name} no disponible — predicciones deshabilitadas para este modelo.")


def get_model(name: str):
    """Devuelve el modelo cargado o None si no está disponible."""
    return _models.get(name)


def models_available() -> list[str]:
    return list(_models.keys())
