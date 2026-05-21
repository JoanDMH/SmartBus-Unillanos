from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from services.ai_analysis import analyze_demand


@pytest.mark.asyncio
async def test_analyze_demand_success():
    """Test successful demand analysis generation by mocking the Groq API call."""
    # Given
    trips = [
        {
            "route_id": "PARQUE",
            "bus_id": "BUS-01",
            "departure_time": datetime(2026, 5, 21, 6, 20),
            "passenger_count": 45,
            "weather": "SOLEADO",
            "academic_week": 8,
            "special_event": False,
        },
        {
            "route_id": "PARQUE",
            "bus_id": "BUS-02",
            "departure_time": datetime(2026, 5, 21, 12, 40),
            "passenger_count": 12,
            "weather": "NUBLADO",
            "academic_week": 8,
            "special_event": True,
        }
    ]

    # Mock the HTTP response from Groq
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value={
        "choices": [
            {
                "message": {
                    "content": "Análisis IA mockeado: alta demanda en la mañana (45 pasajeros), baja demanda al mediodía (12 pasajeros)."
                }
            }
        ]
    })

    # When: Patch the post method on httpx.AsyncClient
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        analysis = await analyze_demand(trips)

        # Then: Verify the HTTP client was called correctly
        mock_post.assert_called_once()
        
        args, kwargs = mock_post.call_args
        assert args[0] == "https://api.groq.com/openai/v1/chat/completions"
        assert "Authorization" in kwargs["headers"]
        
        payload = kwargs["json"]
        assert payload["model"] == "llama-3.1-8b-instant"
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"
        assert "transporte universitario" in payload["messages"][0]["content"]
        assert payload["messages"][1]["role"] == "user"
        
        # Verify the prompt includes our trip data
        prompt_content = payload["messages"][1]["content"]
        assert "Ruta PARQUE" in prompt_content
        assert "Bus BUS-01" in prompt_content
        assert "Pasajeros: 45" in prompt_content
        assert "Pasajeros: 12" in prompt_content

        # Verify returned content matches mock response
        assert "Análisis IA mockeado" in analysis


@pytest.mark.asyncio
async def test_analyze_demand_empty_trips():
    """Test that analyze_demand raises a ValueError when the trip list is empty."""
    # When / Then
    with pytest.raises(ValueError, match="No hay suficientes datos para el análisis."):
        await analyze_demand([])
