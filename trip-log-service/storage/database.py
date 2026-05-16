"""PostgreSQL storage layer — replaces in_memory.py for persistent data."""

import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import DATABASE_URL


# ── ORM Base ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


class TripRow(Base):
    """Persistent trip record stored in PostgreSQL."""

    __tablename__ = "trips"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    route_id = Column(String(50), nullable=False)
    bus_id = Column(String(50), nullable=False)
    departure_time = Column(DateTime(timezone=True), nullable=False)
    passenger_count = Column(Integer, nullable=False)
    weather = Column(String(20), nullable=False, default="SOLEADO")
    academic_week = Column(Integer, nullable=False, default=1)
    special_event = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=True)
    registered_by = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


# ── Engine & Session ──────────────────────────────────────────────────
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Create all tables if they do not exist (dev convenience)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    """FastAPI dependency — yields an async DB session."""
    async with async_session() as session:
        yield session


# ── CRUD helpers ──────────────────────────────────────────────────────
def _row_to_dict(row: TripRow) -> dict:
    """Convert a TripRow ORM instance to a plain dict."""
    return {
        "id": row.id,
        "route_id": row.route_id,
        "bus_id": row.bus_id,
        "departure_time": row.departure_time,
        "passenger_count": row.passenger_count,
        "weather": row.weather,
        "academic_week": row.academic_week,
        "special_event": row.special_event,
        "notes": row.notes,
        "registered_by": row.registered_by,
        "created_at": row.created_at,
    }


async def save_trip(session: AsyncSession, trip: dict) -> dict:
    """Insert a new trip record and return it as a dict."""
    row = TripRow(**trip)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _row_to_dict(row)


async def get_all_trips(
    session: AsyncSession,
    route_id: str | None = None,
    date: str | None = None,
) -> list[dict]:
    """Return all trips, optionally filtered by route_id and/or date."""
    stmt = select(TripRow).order_by(TripRow.departure_time.desc())

    if route_id:
        stmt = stmt.where(TripRow.route_id == route_id)

    result = await session.execute(stmt)
    rows = result.scalars().all()

    # Apply date filter in Python (keeps it simple for any TZ edge-cases)
    if date:
        rows = [r for r in rows if r.departure_time.strftime("%Y-%m-%d") == date]

    return [_row_to_dict(r) for r in rows]


async def get_trip_by_id(session: AsyncSession, trip_id: str) -> dict | None:
    """Return a single trip by its id, or None."""
    stmt = select(TripRow).where(TripRow.id == trip_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return _row_to_dict(row) if row else None


async def compute_stats(session: AsyncSession) -> dict:
    """Compute summary statistics over all stored trips."""
    stmt = select(TripRow)
    result = await session.execute(stmt)
    rows = result.scalars().all()

    if not rows:
        return {
            "total_trips": 0,
            "average_passengers": 0.0,
            "max_passengers": 0,
            "min_passengers": 0,
            "busiest_hour": None,
        }

    counts = [r.passenger_count for r in rows]
    total = len(counts)
    avg = round(sum(counts) / total, 1)

    # Busiest hour: the hour with the highest average passenger count
    hour_totals: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        hour_key = r.departure_time.strftime("%H:00")
        hour_totals[hour_key].append(r.passenger_count)

    busiest_hour = max(
        hour_totals,
        key=lambda h: sum(hour_totals[h]) / len(hour_totals[h]),
    )

    return {
        "total_trips": total,
        "average_passengers": avg,
        "max_passengers": max(counts),
        "min_passengers": min(counts),
        "busiest_hour": busiest_hour,
    }
