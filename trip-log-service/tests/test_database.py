from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from storage.database import save_trip, get_all_trips, get_trip_by_id, compute_stats


@pytest.mark.asyncio
async def test_save_and_retrieve_trip(db_session: AsyncSession):
    """Test saving a new trip and retrieving it by ID."""
    # Given
    trip_data = {
        "route_id": "PARQUE",
        "bus_id": "BUS-99",
        "departure_time": datetime(2026, 5, 21, 8, 30, tzinfo=timezone.utc),
        "passenger_count": 42,
        "weather": "SOLEADO",
        "academic_week": 8,
        "special_event": True,
        "notes": "Parciales de cálculo",
        "registered_by": "conductor1",
    }

    # When
    saved_trip = await save_trip(db_session, trip_data)

    # Then
    assert saved_trip["id"] is not None
    assert saved_trip["route_id"] == "PARQUE"
    assert saved_trip["bus_id"] == "BUS-99"
    assert saved_trip["passenger_count"] == 42
    assert saved_trip["weather"] == "SOLEADO"
    assert saved_trip["academic_week"] == 8
    assert saved_trip["special_event"] is True
    assert saved_trip["notes"] == "Parciales de cálculo"
    assert saved_trip["registered_by"] == "conductor1"

    # Now retrieve it
    retrieved = await get_trip_by_id(db_session, saved_trip["id"])
    assert retrieved is not None
    assert retrieved["id"] == saved_trip["id"]
    assert retrieved["bus_id"] == "BUS-99"


@pytest.mark.asyncio
async def test_get_all_trips_filtering(db_session: AsyncSession):
    """Test retrieving trips with route and date filters."""
    # Given: Insert three trips
    t1 = {
        "route_id": "PARQUE",
        "bus_id": "BUS-01",
        "departure_time": datetime(2026, 5, 21, 6, 20, tzinfo=timezone.utc),
        "passenger_count": 30,
        "weather": "SOLEADO",
        "registered_by": "conductor1",
    }
    t2 = {
        "route_id": "COVISAN",
        "bus_id": "BUS-02",
        "departure_time": datetime(2026, 5, 21, 7, 20, tzinfo=timezone.utc),
        "passenger_count": 50,
        "weather": "NUBLADO",
        "registered_by": "conductor1",
    }
    t3 = {
        "route_id": "PARQUE",
        "bus_id": "BUS-01",
        "departure_time": datetime(2026, 5, 22, 6, 20, tzinfo=timezone.utc),
        "passenger_count": 15,
        "weather": "LLUVIOSO",
        "registered_by": "conductor1",
    }

    await save_trip(db_session, t1)
    await save_trip(db_session, t2)
    await save_trip(db_session, t3)

    # When/Then: 1. Get all trips (should be sorted by departure_time desc)
    all_trips = await get_all_trips(db_session)
    assert len(all_trips) == 3
    # Check sorting: t3 is May 22, t2 is May 21 7:20, t1 is May 21 6:20
    assert all_trips[0]["route_id"] == "PARQUE"  # May 22
    assert all_trips[1]["route_id"] == "COVISAN"  # May 21 7:20
    assert all_trips[2]["route_id"] == "PARQUE"  # May 21 6:20

    # 2. Filter by route_id
    parque_trips = await get_all_trips(db_session, route_id="PARQUE")
    assert len(parque_trips) == 2
    assert all(t["route_id"] == "PARQUE" for t in parque_trips)

    # 3. Filter by date
    may_21_trips = await get_all_trips(db_session, date="2026-05-21")
    assert len(may_21_trips) == 2
    assert all(t["departure_time"].strftime("%Y-%m-%d") == "2026-05-21" for t in may_21_trips)


@pytest.mark.asyncio
async def test_compute_stats_empty(db_session: AsyncSession):
    """Test computing summary statistics on an empty database."""
    # When
    stats = await compute_stats(db_session)

    # Then
    assert stats["total_trips"] == 0
    assert stats["average_passengers"] == 0.0
    assert stats["max_passengers"] == 0
    assert stats["min_passengers"] == 0
    assert stats["busiest_hour"] is None


@pytest.mark.asyncio
async def test_compute_stats_populated(db_session: AsyncSession):
    """Test computing summary statistics on a populated database."""
    # Given: Insert three trips with varying passenger counts and times
    t1 = {
        "route_id": "PARQUE",
        "bus_id": "BUS-01",
        "departure_time": datetime(2026, 5, 21, 6, 20, tzinfo=timezone.utc),  # 06:00 slot
        "passenger_count": 40,
        "registered_by": "conductor1",
    }
    t2 = {
        "route_id": "PARQUE",
        "bus_id": "BUS-02",
        "departure_time": datetime(2026, 5, 21, 6, 40, tzinfo=timezone.utc),  # 06:00 slot
        "passenger_count": 60,
        "registered_by": "conductor1",
    }
    t3 = {
        "route_id": "PARQUE",
        "bus_id": "BUS-03",
        "departure_time": datetime(2026, 5, 21, 8, 30, tzinfo=timezone.utc),  # 08:00 slot
        "passenger_count": 20,
        "registered_by": "conductor1",
    }

    await save_trip(db_session, t1)
    await save_trip(db_session, t2)
    await save_trip(db_session, t3)

    # When
    stats = await compute_stats(db_session)

    # Then
    # Total = 3 trips
    # Max = 60, Min = 20
    # Average = (40 + 60 + 20) / 3 = 40.0
    # Busiest hour = "06:00" because it has average (40+60)/2 = 50 passengers, vs "08:00" which has 20.
    assert stats["total_trips"] == 3
    assert stats["average_passengers"] == 40.0
    assert stats["max_passengers"] == 60
    assert stats["min_passengers"] == 20
    assert stats["busiest_hour"] == "06:00"
