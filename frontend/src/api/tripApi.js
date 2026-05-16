// Uses env var in production builds, falls back to empty for local dev (Vite proxy)
const TRIP_BASE = import.meta.env.VITE_TRIP_LOG_BASE_URL || '';

function authHeaders(token) {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

/**
 * GET /routes — public, no auth.
 */
export async function getRoutes() {
  const res = await fetch(`${TRIP_BASE}/routes`);
  if (!res.ok) throw new Error('Error al obtener rutas');
  return res.json();
}

/**
 * GET /trips — protected.
 */
export async function getTrips(token, { routeId, date } = {}) {
  const params = new URLSearchParams();
  if (routeId) params.set('route_id', routeId);
  if (date) params.set('date', date);
  const qs = params.toString();

  const res = await fetch(`${TRIP_BASE}/trips${qs ? '?' + qs : ''}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Error al obtener viajes');
  return res.json();
}

/**
 * POST /trips — protected.
 */
export async function createTrip(token, tripData) {
  const res = await fetch(`${TRIP_BASE}/trips`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(tripData),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || 'Error al registrar viaje');
  }
  return res.json();
}

/**
 * GET /trips/stats/summary — protected.
 */
export async function getTripStats(token) {
  const res = await fetch(`${TRIP_BASE}/trips/stats/summary`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Error al obtener estadísticas');
  return res.json();
}

/**
 * GET /trips/ai/demand-analysis — protected.
 * Returns { analysis: string } with AI-generated demand insights.
 */
export async function getDemandAnalysis(token) {
  const res = await fetch(`${TRIP_BASE}/trips/ai/demand-analysis`, {
    headers: authHeaders(token),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || 'Error al obtener análisis de IA');
  }
  return res.json();
}
