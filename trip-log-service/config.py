"""Application configuration — loads environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET: str = os.getenv("JWT_SECRET", "THIS_IS_A_DEMO_KEY_CHANGE_IT_123456789")
JWT_ISSUER: str = os.getenv("JWT_ISSUER", "MiniIdentityApi")
JWT_AUDIENCE: str = os.getenv("JWT_AUDIENCE", "MiniIdentityApiUsers")
PORT: int = int(os.getenv("PORT", "8000"))

# PostgreSQL connection string (async driver)
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://smartbus:smartbus123@localhost:5432/smartbus",
)

# Groq API key for AI demand analysis
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

# OpenWeatherMap — auto-capture weather on trip registration (DEV-A3)
OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
OPENWEATHER_CITY: str = os.getenv("OPENWEATHER_CITY", "Villavicencio,CO")

# Azure Blob Storage — model artifact storage (DEV-B4)
AZURE_STORAGE_CONNECTION_STRING: str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
AZURE_MODEL_CONTAINER: str = os.getenv("AZURE_MODEL_CONTAINER", "smartbus-models")
MODEL_LOCAL_CACHE_PATH: str = os.getenv("MODEL_LOCAL_CACHE_PATH", "/tmp/smartbus_models")

# Optimization service URL (DEV-C1/C3)
OPTIMIZATION_SERVICE_URL: str = os.getenv("OPTIMIZATION_SERVICE_URL", "http://localhost:8001")
