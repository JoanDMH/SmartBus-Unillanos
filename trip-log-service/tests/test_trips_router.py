import pytest
import httpx
from unittest.mock import AsyncMock, patch
from main import app
from auth.jwt_validator import get_current_user
from storage.database import get_session


@pytest.fixture
def override_dependencies(db_session):
    """Override FastAPI dependencies to bypass auth and inject test DB session."""
    # Bypass JWT authentication and return a fixed username
    app.dependency_overrides[get_current_user] = lambda: "conductor_test"
    # Inject our testing db_session (with automatic transactional rollback)
    app.dependency_overrides[get_session] = lambda: db_session
    
    yield
    
    # Clean up overrides after test
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_and_list_trips(override_dependencies, db_session):
    """Test POST /trips and GET /trips endpoints using ASGI test client."""
    # Given: ASGI Transport client
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        
        # When: Post a new trip
        payload = {
            "route_id": "PARQUE",
            "departure_time": "2026-05-21T06:20:00Z",
            "passenger_count": 45,
            "bus_id": "BUS-10",
            "weather": "SOLEADO",
            "academic_week": 8,
            "special_event": False,
            "notes": "Parciales de telemática"
        }
        response = await client.post("/trips", json=payload)
        
        # Then: Check HTTP 201 Created and response content
        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["route_id"] == "PARQUE"
        assert data["bus_id"] == "BUS-10"
        assert data["passenger_count"] == 45
        assert data["registered_by"] == "conductor_test"

        # When: List trips
        list_response = await client.get("/trips")
        
        # Then: Check HTTP 200 and listed trips
        assert list_response.status_code == 200
        trips = list_response.json()
        assert len(trips) == 1
        assert trips[0]["id"] == data["id"]


@pytest.mark.asyncio
async def test_get_trip_stats_summary(override_dependencies, db_session):
    """Test GET /trips/stats/summary returns calculated statistics."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        
        # Create multiple trips to compute stats
        payload1 = {
            "route_id": "PARQUE", "departure_time": "2026-05-21T06:20:00Z",
            "passenger_count": 40, "bus_id": "BUS-10", "weather": "SOLEADO"
        }
        payload2 = {
            "route_id": "PARQUE", "departure_time": "2026-05-21T06:40:00Z",
            "passenger_count": 60, "bus_id": "BUS-11", "weather": "SOLEADO"
        }
        await client.post("/trips", json=payload1)
        await client.post("/trips", json=payload2)

        # Get stats
        stats_response = await client.get("/trips/stats/summary")
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert stats["total_trips"] == 2
        assert stats["average_passengers"] == 50.0
        assert stats["max_passengers"] == 60
        assert stats["min_passengers"] == 40
        assert stats["busiest_hour"] == "06:00"


@pytest.mark.asyncio
async def test_demand_analysis_success(override_dependencies, db_session):
    """Test GET /trips/ai/demand-analysis endpoint when Groq succeeds."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        
        # Create at least one trip so we have data to analyze
        payload = {
            "route_id": "PARQUE", "departure_time": "2026-05-21T06:20:00Z",
            "passenger_count": 40, "bus_id": "BUS-10", "weather": "SOLEADO"
        }
        await client.post("/trips", json=payload)

        # Mock the analyze_demand function inside router to return a mock string
        with patch("routers.trips_router.analyze_demand", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = "Análisis IA Router: Alta demanda detectada en la hora pico."
            
            response = await client.get("/trips/ai/demand-analysis")
            
            assert response.status_code == 200
            assert response.json() == {"analysis": "Análisis IA Router: Alta demanda detectada en la hora pico."}
            mock_analyze.assert_called_once()


@pytest.mark.asyncio
async def test_demand_analysis_no_data(override_dependencies, db_session):
    """Test GET /trips/ai/demand-analysis returns 400 when no trips exist in database."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        
        # Call AI analysis on an empty database
        response = await client.get("/trips/ai/demand-analysis")
        
        assert response.status_code == 400
        assert "No hay suficientes datos" in response.json()["detail"]


@pytest.mark.asyncio
async def test_demand_analysis_ai_gateway_error(override_dependencies, db_session):
    """Test GET /trips/ai/demand-analysis returns 502 when Groq API fails."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        
        # Create at least one trip so we have data
        payload = {
            "route_id": "PARQUE", "departure_time": "2026-05-21T06:20:00Z",
            "passenger_count": 40, "bus_id": "BUS-10", "weather": "SOLEADO"
        }
        await client.post("/trips", json=payload)

        # Mock analyze_demand to raise an exception (simulating gateway timeout or API error)
        with patch("routers.trips_router.analyze_demand", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = Exception("Groq API Timeout")
            
            response = await client.get("/trips/ai/demand-analysis")
            
            assert response.status_code == 502
            assert "Error al consultar el servicio de IA" in response.json()["detail"]
