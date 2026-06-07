"""Trips router — protected CRUD, statistics, and AI analysis endpoints."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt_validator import get_current_user
from models.trip import TripCreate, TripResponse
from services.ai_analysis import analyze_demand
from services.weather_client import get_current_weather
from storage.database import (
    compute_stats,
    get_all_trips,
    get_session,
    get_trip_by_id,
    save_trip,
)

router = APIRouter()


@router.post("/trips", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    body: TripCreate,
    user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Register a new trip record.

    If ``weather`` is omitted in the request body, the current weather for
    Villavicencio is fetched automatically from OpenWeatherMap (DEV-A3).
    """
    # Auto-capture weather when not provided by the driver
    weather_value: str
    if body.weather is not None:
        weather_value = body.weather.value
    else:
        weather_value = await get_current_weather()

    trip = {
        "id": str(uuid.uuid4()),
        "route_id": body.route_id,
        "departure_time": body.departure_time,
        "passenger_count": body.passenger_count,
        "bus_id": body.bus_id,
        "weather": weather_value,
        "academic_week": body.academic_week,
        "special_event": body.special_event,
        "notes": body.notes,
        "registered_by": user,
        "created_at": datetime.now(timezone.utc),
    }
    saved = await save_trip(session, trip)
    return saved


@router.get("/trips/stats/summary")
async def trip_stats(
    user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Return occupancy summary statistics.

     This route is registered before ``/trips/{trip_id}`` so FastAPI
    does not interpret ``"stats"`` as a path parameter.
    """
    return await compute_stats(session)


@router.get("/trips/ai/demand-analysis")
async def demand_analysis(
    user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Analyze trip demand patterns using AI (Groq LLM).

    Reads all trips from PostgreSQL, builds a structured prompt,
    and returns a natural-language analysis in Spanish.
    """
    trips = await get_all_trips(session)
    # Limit to the 30 most recent trips to avoid payload size and token rate limits on free Groq keys
    trips = trips[:30]

    if not trips:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay suficientes datos para el análisis.",
        )

    try:
        analysis = await analyze_demand(trips)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al consultar el servicio de IA: {str(exc)}",
        )

    return {"analysis": analysis}


@router.get("/trips", response_model=list[TripResponse])
async def list_trips(
    route_id: str | None = Query(None),
    date: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List trips, optionally filtered by route and/or date (YYYY-MM-DD)."""
    return await get_all_trips(session, route_id=route_id, date=date)


@router.get("/trips/{trip_id}", response_model=TripResponse)
async def get_trip(
    trip_id: str,
    user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get a single trip by ID."""
    trip = await get_trip_by_id(session, trip_id)
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )
    return trip
