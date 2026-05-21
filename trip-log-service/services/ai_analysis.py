"""AI demand analysis service — calls Groq API for intelligent trip analysis."""

import httpx

from config import GROQ_API_KEY


async def analyze_demand(trips: list[dict]) -> str:
    """Build a prompt from trip data and query Groq for demand analysis.

    Args:
        trips: List of trip dicts with route_id, bus_id, departure_time,
               passenger_count, weather, academic_week, special_event.

    Returns:
        Natural-language analysis string in Spanish.

    Raises:
        ValueError: If there are no trips to analyze.
        httpx.HTTPStatusError: If the Groq API returns an error.
    """
    if not trips:
        raise ValueError("No hay suficientes datos para el análisis.")

    lines = []
    for t in trips:
        dep_time = t["departure_time"]
        time_str = dep_time.strftime("%H:%M") if hasattr(dep_time, "strftime") else str(dep_time)
        date_str = dep_time.strftime("%Y-%m-%d") if hasattr(dep_time, "strftime") else ""
        weather = t.get("weather", "N/A")
        academic_week = t.get("academic_week", "N/A")
        special = "Sí" if t.get("special_event") else "No"

        lines.append(
            f"- Ruta {t['route_id']} | Bus {t['bus_id']} | "
            f"Fecha: {date_str} | Salida: {time_str} | "
            f"Pasajeros: {t['passenger_count']} | "
            f"Clima: {weather} | Semana: {academic_week} | "
            f"Evento especial: {special}"
        )

    data_summary = "\n".join(lines)

    prompt = (
        f"Analiza los siguientes registros de viajes del transporte universitario "
        f"de la Universidad de los Llanos (Ruta Parque, Villavicencio) y genera "
        f"recomendaciones concretas sobre la distribución de demanda por franja "
        f"horaria. Incluye patrones identificados y sugerencias de optimización "
        f"de frecuencia:\n\n{data_summary}"
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Eres un asistente experto en análisis de transporte "
                            "universitario. Analiza datos de ocupación de buses y "
                            "genera recomendaciones claras y concisas en español. "
                            "Máximo 5 oraciones. Enfócate en patrones de demanda "
                            "por hora, día y condiciones climáticas, y sugiere "
                            "ajustes de frecuencia."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 400,
                "temperature": 0.7,
            },
        )
        response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]
