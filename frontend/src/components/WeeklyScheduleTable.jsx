/**
 * DEV-D2 — WeeklyScheduleTable
 * Tabla editable del itinerario semanal generado por el optimizador.
 * Permite al despachador ajustar manualmente el número de buses por franja
 * antes de aprobar el itinerario.
 *
 * Props:
 *   scheduleByDay   { lunes: [{hour, buses_dispatched, demand_forecast, cost_cop}], ... }
 *   onEdit          (day, hour, newBuses) => void
 *   readOnly        bool — oculta los inputs de edición (para vista de aprobados)
 */

const WEEKDAYS = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado'];
const DAY_LABELS = { lunes: 'Lunes', martes: 'Martes', miercoles: 'Miércoles', jueves: 'Jueves', viernes: 'Viernes', sabado: 'Sábado' };

function formatCOP(value) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(value);
}

export default function WeeklyScheduleTable({ scheduleByDay = {}, onEdit, readOnly = false }) {
  if (!scheduleByDay || !Object.keys(scheduleByDay).length) {
    return (
      <div style={{ color: 'var(--text-secondary, #8b949e)', fontSize: 14, padding: '1rem 0' }}>
        Sin datos de itinerario.
      </div>
    );
  }

  // Calcular totales por día
  const totals = WEEKDAYS.reduce((acc, day) => {
    const entries = scheduleByDay[day] || [];
    acc[day] = {
      buses: entries.reduce((s, e) => s + (e.buses_dispatched || 0), 0),
      cost: entries.reduce((s, e) => s + (e.cost_cop || 0), 0),
    };
    return acc;
  }, {});

  return (
    <div style={{ overflowX: 'auto' }}>
      {WEEKDAYS.map((day) => {
        const entries = scheduleByDay[day];
        if (!entries?.length) return null;

        return (
          <div key={day} style={{ marginBottom: '1.5rem' }}>
            {/* Día header */}
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              marginBottom: 8, paddingBottom: 6,
              borderBottom: '1px solid var(--border, #30363d)',
            }}>
              <span style={{ fontWeight: 600, color: 'var(--text-primary, #e6edf3)', fontSize: 14 }}>
                {DAY_LABELS[day]}
              </span>
              <span style={{ fontSize: 12, color: 'var(--text-secondary, #8b949e)' }}>
                {totals[day].buses} despachos · {formatCOP(totals[day].cost)}
              </span>
            </div>

            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ color: 'var(--text-secondary, #8b949e)' }}>
                  <th style={thStyle}>Hora</th>
                  <th style={thStyle}>Demanda predicha</th>
                  <th style={thStyle}>Buses despachados</th>
                  <th style={thStyle}>Pasajeros cubiertos</th>
                  <th style={thStyle}>Costo COP</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => {
                  const coverage = entry.passengers_covered ?? (entry.buses_dispatched * 40);
                  const sufficient = coverage >= Math.ceil(entry.demand_forecast || 0);
                  return (
                    <tr key={entry.hour} style={{ borderBottom: '1px solid var(--border-subtle, #21262d)' }}>
                      <td style={tdStyle}>
                        <span style={{
                          fontFamily: 'monospace',
                          background: 'var(--bg-subtle, #161b22)',
                          padding: '2px 8px',
                          borderRadius: 4,
                          fontSize: 12,
                        }}>
                          {String(entry.hour).padStart(2, '0')}:00
                        </span>
                      </td>
                      <td style={tdStyle}>
                        <span style={{ color: 'var(--text-secondary, #8b949e)' }}>
                          {Math.round(entry.demand_forecast ?? 0)} pas.
                        </span>
                      </td>
                      <td style={tdStyle}>
                        {readOnly ? (
                          <span style={{ color: 'var(--text-primary, #e6edf3)', fontWeight: 600 }}>
                            {entry.buses_dispatched}
                          </span>
                        ) : (
                          <input
                            type="number"
                            min={0}
                            max={10}
                            value={entry.buses_dispatched}
                            onChange={(e) => onEdit?.(day, entry.hour, Number(e.target.value))}
                            style={{
                              width: 60,
                              background: 'var(--input-bg, #0d1117)',
                              border: '1px solid var(--border, #30363d)',
                              color: 'var(--text-primary, #e6edf3)',
                              borderRadius: 6,
                              padding: '3px 8px',
                              fontSize: 13,
                              textAlign: 'center',
                            }}
                          />
                        )}
                      </td>
                      <td style={tdStyle}>
                        <span style={{ color: sufficient ? '#3fb950' : '#f85149', fontWeight: 600 }}>
                          {coverage} pas.
                        </span>
                        {!sufficient && (
                          <span style={{ marginLeft: 6, fontSize: 11, color: '#f85149' }}>⚠ insuf.</span>
                        )}
                      </td>
                      <td style={{ ...tdStyle, color: 'var(--text-secondary, #8b949e)', fontFamily: 'monospace', fontSize: 12 }}>
                        {formatCOP(entry.cost_cop ?? 0)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        );
      })}
    </div>
  );
}

const thStyle = {
  textAlign: 'left',
  padding: '6px 12px',
  fontWeight: 500,
  fontSize: 12,
  borderBottom: '1px solid var(--border, #30363d)',
};

const tdStyle = {
  padding: '7px 12px',
  verticalAlign: 'middle',
};
