"""Trip Pydantic models — input and output."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Weather(str, Enum):
    """Condición climática al momento de la salida."""
    SOLEADO = "SOLEADO"
    NUBLADO = "NUBLADO"
    LLUVIOSO = "LLUVIOSO"


class TripCreate(BaseModel):
    route_id: str
    departure_time: datetime
    passenger_count: int = Field(ge=0, le=100)
    bus_id: str
    weather: Weather | None = None  # None → auto-fetched from OpenWeatherMap (DEV-A3)
    academic_week: int = Field(ge=1, le=18, default=1)
    special_event: bool = False
    notes: str | None = None


class TripResponse(BaseModel):
    id: str
    route_id: str
    departure_time: datetime
    passenger_count: int
    bus_id: str
    weather: Weather
    academic_week: int
    special_event: bool
    notes: str | None
    registered_by: str  # username extracted from JWT
    created_at: datetime
