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
