"""Sube artefactos .pkl a Azure Blob Storage.

Si AZURE_STORAGE_CONNECTION_STRING no está configurada (ej. entorno local),
la subida se omite silenciosamente.
"""

import os
from dotenv import load_dotenv

load_dotenv()

CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
CONTAINER_NAME    = os.getenv("AZURE_MODEL_CONTAINER", "smartbus-models")


def upload_artifact(local_path: str, blob_name: str) -> None:
    if not CONNECTION_STRING:
        print(f"[Upload] AZURE_STORAGE_CONNECTION_STRING no configurada — omitiendo subida de {blob_name}.")
        return
    try:
        from azure.storage.blob import BlobServiceClient
        client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
        container = client.get_container_client(CONTAINER_NAME)
        try:
            container.create_container()
        except Exception:
            pass  # ya existe
        with open(local_path, "rb") as f:
            container.upload_blob(name=blob_name, data=f, overwrite=True)
        print(f"[Upload] {blob_name} subido a Azure Blob ({CONTAINER_NAME}).")
    except Exception as e:
        print(f"[Upload] ERROR subiendo {blob_name}: {e}")
