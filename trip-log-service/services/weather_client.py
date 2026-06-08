"""Async OpenWeatherMap client — auto-captura el clima actual de Villavicencio.

El plan gratuito de OpenWeatherMap permite 1.000 llamadas/día. Sin caché,
múltiples registros de viaje en poco tiempo agotarían la cuota rápidamente.

Caché TTL: las respuestas se almacenan en memoria durante CACHE_TTL_SECONDS
(600 s = 10 minutos). Dado que el clima en Villavicencio no cambia cada
segundo, 10 min es un balance razonable entre frescura y ahorro de cuota.

Mapeo de condiciones OWM → enum Weather del modelo:
  - Thunderstorm, Drizzle, Rain, Snow → LLUVIOSO
  - Clouds, Mist, Fog, Haze, ...      → NUBLADO
  - Clear                              → SOLEADO
"""

import time
from typing import Optional

import httpx

from config import OPENWEATHER_API_KEY, OPENWEATHER_CITY

# OWM condition group IDs: https://openweathermap.org/weather-conditions
_RAINY_IDS  = range(200, 700)   # 2xx Thunderstorm, 3xx Drizzle, 5xx Rain, 6xx Snow
_CLOUDY_IDS = range(700, 800)   # 7xx Atmosphere (mist, fog, haze, smoke…)
# 800 = Clear, 80x = Clouds (handled below)

OWM_URL = "https://api.openweathermap.org/data/2.5/weather"

# ── Caché en memoria ────────────────────────────────────────────────────────
CACHE_TTL_SECONDS: int = 600    # 10 minutos

_cache_value: Optional[str] = None
_cache_ts: float = 0.0          # epoch seconds del último fetch exitoso


async def get_current_weather() -> str:
    """Devuelve 'SOLEADO', 'NUBLADO' o 'LLUVIOSO' según el clima actual.

    Cachea la respuesta durante CACHE_TTL_SECONDS para no agotar la cuota
    gratuita de OWM (1.000 llamadas/día).

    Si la API key no está configurada o la llamada falla, devuelve 'NUBLADO'
    como valor seguro por defecto sin lanzar excepción (degradación elegante).
    """
    global _cache_value, _cache_ts

    if not OPENWEATHER_API_KEY:
        return "NUBLADO"

    # Devolver valor cacheado si está dentro del TTL
    if _cache_value is not None and (time.monotonic() - _cache_ts) < CACHE_TTL_SECONDS:
        return _cache_value

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
        # En caso de error, devolver el último valor conocido o el fallback
        return _cache_value if _cache_value is not None else "NUBLADO"

    condition_id: int = data["weather"][0]["id"]

    if condition_id in _RAINY_IDS:
        result = "LLUVIOSO"
    elif condition_id in _CLOUDY_IDS:
        result = "NUBLADO"
    elif condition_id == 800:
        result = "SOLEADO"
    else:
        # 801–804: partly cloudy → NUBLADO
        result = "NUBLADO"

    # Actualizar caché
    _cache_value = result
    _cache_ts = time.monotonic()
    return result
