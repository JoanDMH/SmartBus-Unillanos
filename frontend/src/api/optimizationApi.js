const TRIP_BASE = import.meta.env.VITE_TRIP_LOG_BASE_URL || '';

function authHeaders(token) {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

/**
 * POST /trips/optimization/weekly-schedule
 * Genera y persiste un nuevo itinerario semanal (status: pending).
 *
 * @param {string} token
 * @param {{ weekLabel, academicWeek, specialEvent, fleet }} body
 */
export async function generateWeeklySchedule(token, body) {
  const res = await fetch(`${TRIP_BASE}/trips/optimization/weekly-schedule`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Error al generar el itinerario');
  }
  return res.json();
}

/**
 * POST /trips/optimization/weekly-schedule/approve
 * Aprueba un itinerario pendiente (human-in-the-loop).
 */
export async function approveSchedule(token, scheduleId) {
  const res = await fetch(`${TRIP_BASE}/trips/optimization/weekly-schedule/approve`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ schedule_id: scheduleId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Error al aprobar el itinerario');
  }
  return res.json();
}

/**
 * GET /trips/optimization/weekly-schedule/latest
 * Devuelve el último itinerario aprobado.
 */
export async function getLatestApprovedSchedule(token, weekLabel) {
  const params = weekLabel ? `?week_label=${weekLabel}` : '';
  const res = await fetch(
    `${TRIP_BASE}/trips/optimization/weekly-schedule/latest${params}`,
    { headers: authHeaders(token) }
  );
  if (res.status === 404) return null;
  if (!res.ok) throw new Error('Error al obtener el itinerario aprobado');
  return res.json();
}

/**
 * GET /trips/optimization/weekly-schedule
 * Lista todos los itinerarios (opcionalmente filtrados por status).
 */
export async function listSchedules(token, status) {
  const params = status ? `?status=${status}` : '';
  const res = await fetch(
    `${TRIP_BASE}/trips/optimization/weekly-schedule${params}`,
    { headers: authHeaders(token) }
  );
  if (!res.ok) throw new Error('Error al listar itinerarios');
  return res.json();
}
