"""Async OpenWeatherMap client — auto-captura el clima actual de Villavicencio.

El plan gratuito de OpenWeatherMap permite 1.000 llamadas/día, suficiente para
el volumen operativo actual de la Ruta Parque.

Mapeo de condiciones OWM → enum Weather del modelo:
  - Thunderstorm, Drizzle, Rain, Snow → LLUVIOSO
  - Clouds, Mist, Fog, Haze, ...      → NUBLADO
  - Clear                              → SOLEADO
"""

import httpx

from config import OPENWEATHER_API_KEY, OPENWEATHER_CITY

# OWM condition group IDs: https://openweathermap.org/weather-conditions
_RAINY_IDS  = range(200, 700)   # 2xx Thunderstorm, 3xx Drizzle, 5xx Rain, 6xx Snow
_CLOUDY_IDS = range(700, 800)   # 7xx Atmosphere (mist, fog, haze, smoke…)
# 800 = Clear, 80x = Clouds (handled below)

OWM_URL = "https://api.openweathermap.org/data/2.5/weather"


async def get_current_weather() -> str:
    """Devuelve 'SOLEADO', 'NUBLADO' o 'LLUVIOSO' según el clima actual.

    Si la API key no está configurada o la llamada falla, devuelve 'NUBLADO'
    como valor seguro por defecto sin lanzar excepción (degradación elegante).
    """
    if not OPENWEATHER_API_KEY:
        return "NUBLADO"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(OWM_URL, params={
                "q":     OPENWEATHER_CITY,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric",
            })
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return "NUBLADO"

    condition_id: int = data["weather"][0]["id"]

    if condition_id in _RAINY_IDS:
        return "LLUVIOSO"
    if condition_id in _CLOUDY_IDS:
        return "NUBLADO"
    if condition_id == 800:
        return "SOLEADO"
    # 801–804: partly cloudy → NUBLADO
    return "NUBLADO"
