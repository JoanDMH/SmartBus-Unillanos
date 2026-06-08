const TRIP_BASE = import.meta.env.VITE_TRIP_LOG_BASE_URL || '';

function authHeaders(token) {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

/**
 * GET /trips/ai/predict-demand
 * Devuelve predicciones de demanda para una fecha dada.
 *
 * @param {string} token  JWT del usuario autenticado
 * @param {string} date   Fecha en formato YYYY-MM-DD
 * @param {Object} opts   { academicWeek, specialEvent, model }
 * @returns {{ model_used, route_id, date, predictions: [{hour, predicted_passengers, confidence_low, confidence_high}] }}
 */
export async function getDemandPrediction(token, date, { academicWeek = 1, specialEvent = false, model = 'best' } = {}) {
  const params = new URLSearchParams({
    date,
    academic_week: academicWeek,
    special_event: specialEvent,
    model_name: model,
  });

  const res = await fetch(`${TRIP_BASE}/trips/ai/predict-demand?${params}`, {
    headers: authHeaders(token),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || 'Error al obtener predicciones');
  }
  return res.json();
}

/**
 * GET /trips — filtrando por fecha, para obtener ocupación real del mismo día.
 * Devuelve { hour, real_passengers } a partir de los viajes registrados.
 */
export async function getRealOccupancy(token, date) {
  const params = new URLSearchParams({ date });
  const res = await fetch(`${TRIP_BASE}/trips?${params}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Error al obtener ocupación real');
  const trips = await res.json();

  // Agregar por hora: promedio de passenger_count
  const byHour = {};
  for (const trip of trips) {
    const hour = new Date(trip.departure_time).getHours();
    if (!byHour[hour]) byHour[hour] = [];
    byHour[hour].push(trip.passenger_count);
  }

  return Array.from({ length: 24 }, (_, h) => ({
    hour: h,
    real_passengers: byHour[h]
      ? Math.round(byHour[h].reduce((a, b) => a + b, 0) / byHour[h].length)
      : null,
  }));
}
