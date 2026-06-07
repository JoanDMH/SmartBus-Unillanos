"""Carga los datos de viajes desde PostgreSQL y los prepara para ML.

Devuelve un DataFrame con columnas:
  ds           datetime  — fecha-hora de salida (UTC)
  y            int       — número de pasajeros
  route_id     str
  weather      str       — SOLEADO | NUBLADO | LLUVIOSO
  academic_week int      — 1-18
  special_event bool
  hour         int       — 0-23
  day_of_week  int       — 0=lunes … 6=domingo
  is_peak      bool      — True si hour in [6,7,8,12,13,17,18]
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://smartbus:smartbus123@localhost:5432/smartbus",
).replace("+asyncpg", "")  # sqlalchemy sync driver para scripts batch


def load_trips(route_id: str | None = None) -> pd.DataFrame:
    engine = create_engine(DATABASE_URL)
    query = "SELECT * FROM trips"
    if route_id:
        query += f" WHERE route_id = '{route_id}'"
    query += " ORDER BY departure_time ASC"

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, parse_dates=["departure_time", "created_at"])

    if df.empty:
        return df

    df = df.rename(columns={"departure_time": "ds", "passenger_count": "y"})
    df["ds"] = pd.to_datetime(df["ds"], utc=True).dt.tz_localize(None)
    df["hour"]         = df["ds"].dt.hour
    df["day_of_week"]  = df["ds"].dt.dayofweek
    df["is_peak"]      = df["hour"].isin([6, 7, 8, 12, 13, 17, 18])

    # One-hot encode weather for XGBoost
    df["weather_soleado"] = (df["weather"] == "SOLEADO").astype(int)
    df["weather_nublado"]  = (df["weather"] == "NUBLADO").astype(int)
    df["weather_lluvioso"] = (df["weather"] == "LLUVIOSO").astype(int)

    return df
