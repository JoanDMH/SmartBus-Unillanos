/**
 * DEV-D1 — PredictionDashboard
 * Dashboard de analíticas predictivas con Recharts.
 *
 * Secciones:
 *   1. Selector de fecha + controles de modelo
 *   2. DemandChart: predicho vs. real por hora del día
 *   3. Heatmap semanal de ocupación (día × hora)
 *   4. Panel de métricas del modelo activo
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import DemandChart from '../components/DemandChart';
import { getDemandPrediction, getRealOccupancy } from '../api/predictionApi';

/* ── Helpers ─────────────────────────────────────────────────────────────── */

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function weekStart(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  return d;
}

const WEEKDAY_LABELS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
const HOUR_LABELS = Array.from({ length: 24 }, (_, h) => `${String(h).padStart(2, '0')}`);

/* ── Icons ───────────────────────────────────────────────────────────────── */

const IconArrowLeft = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="15 18 9 12 15 6" />
  </svg>
);

const IconCalendar = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" />
  </svg>
);

const IconCpu = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="4" y="4" width="16" height="16" rx="2" /><rect x="9" y="9" width="6" height="6" />
    <line x1="9" y1="1" x2="9" y2="4" /><line x1="15" y1="1" x2="15" y2="4" />
    <line x1="9" y1="20" x2="9" y2="23" /><line x1="15" y1="20" x2="15" y2="23" />
    <line x1="20" y1="9" x2="23" y2="9" /><line x1="20" y1="14" x2="23" y2="14" />
    <line x1="1" y1="9" x2="4" y2="9" /><line x1="1" y1="14" x2="4" y2="14" />
  </svg>
);

/* ── Heatmap semanal ─────────────────────────────────────────────────────── */

function WeekHeatmap({ weekData }) {
  if (!weekData || weekData.every((d) => !d?.predictions?.length)) {
    return (
      <div style={{ color: 'var(--text-secondary, #8b949e)', fontSize: 14, padding: '1rem 0' }}>
        Sin datos de predicción para esta semana.
      </div>
    );
  }

  // Max value for color scale
  const allValues = weekData.flatMap((d) =>
    (d?.predictions || []).map((p) => p.predicted_passengers)
  );
  const maxVal = Math.max(...allValues, 1);

  function cellColor(value) {
    if (value === null || value === undefined) return 'var(--bg-subtle, #161b22)';
    const intensity = value / maxVal;
    // Blue ramp: low → #0d1117, high → #1f6feb
    const r = Math.round(15 + intensity * (31 - 15));
    const g = Math.round(17 + intensity * (111 - 17));
    const b = Math.round(23 + intensity * (235 - 23));
    return `rgb(${r},${g},${b})`;
  }

  // Peak hours only (5–21) to keep the heatmap legible
  const visibleHours = Array.from({ length: 17 }, (_, i) => i + 5);

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ borderCollapse: 'collapse', fontSize: 11, width: '100%' }}>
        <thead>
          <tr>
            <th style={{ width: 36, color: 'var(--text-secondary, #8b949e)', fontWeight: 400 }} />
            {visibleHours.map((h) => (
              <th key={h} style={{ width: 32, textAlign: 'center', color: 'var(--text-secondary, #8b949e)', fontWeight: 400, paddingBottom: 4 }}>
                {String(h).padStart(2, '0')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {WEEKDAY_LABELS.map((label, di) => {
            const dayPreds = weekData[di]?.predictions || [];
            return (
              <tr key={label}>
                <td style={{ color: 'var(--text-secondary, #8b949e)', paddingRight: 6, textAlign: 'right', fontSize: 11 }}>
                  {label}
                </td>
                {visibleHours.map((h) => {
                  const pred = dayPreds.find((p) => p.hour === h);
                  const val = pred?.predicted_passengers ?? null;
                  return (
                    <td
                      key={h}
                      title={val !== null ? `${label} ${String(h).padStart(2,'0')}:00 — ${val} pas.` : ''}
                      style={{
                        width: 28,
                        height: 22,
                        background: cellColor(val),
                        borderRadius: 3,
                        margin: 1,
                        cursor: val !== null ? 'default' : 'not-allowed',
                      }}
                    />
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Color scale legend */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 10, fontSize: 11, color: 'var(--text-secondary, #8b949e)' }}>
        <span>0</span>
        <div style={{
          flex: 1, height: 8, borderRadius: 4,
          background: 'linear-gradient(to right, #0d1117, #1f6feb)',
          maxWidth: 120,
        }} />
        <span>{maxVal} pas.</span>
      </div>
    </div>
  );
}

/* ── Panel de métricas del modelo ────────────────────────────────────────── */

function ModelMetrics({ modelUsed }) {
  if (!modelUsed) return null;
  const name = modelUsed === 'model_prophet' ? 'Prophet' : 'XGBoost';
  const color = modelUsed === 'model_prophet' ? '#f78166' : '#d2a679';

  return (
    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
      <div className="card stat-card" style={{ minWidth: 120, padding: '1rem' }}>
        <div style={{ fontSize: 11, color: 'var(--text-secondary, #8b949e)', marginBottom: 4 }}>Modelo activo</div>
        <div style={{ fontWeight: 700, color, fontSize: 15 }}>{name}</div>
      </div>
      <div className="card stat-card" style={{ minWidth: 120, padding: '1rem' }}>
        <div style={{ fontSize: 11, color: 'var(--text-secondary, #8b949e)', marginBottom: 4 }}>Umbral MAE</div>
        <div style={{ fontWeight: 700, color: '#3fb950', fontSize: 15 }}>≤ 5 pas.</div>
      </div>
      <div className="card stat-card" style={{ minWidth: 140, padding: '1rem' }}>
        <div style={{ fontSize: 11, color: 'var(--text-secondary, #8b949e)', marginBottom: 4 }}>Ruta</div>
        <div style={{ fontWeight: 700, color: '#e6edf3', fontSize: 15 }}>Parque Unillanos</div>
      </div>
    </div>
  );
}

/* ── Página principal ────────────────────────────────────────────────────── */

export default function PredictionDashboard() {
  const { token } = useAuth();
  const navigate = useNavigate();

  const [selectedDate, setSelectedDate] = useState(todayISO());
  const [academicWeek, setAcademicWeek] = useState(1);
  const [specialEvent, setSpecialEvent] = useState(false);

  const [predictions, setPredictions] = useState([]);
  const [realData, setRealData] = useState([]);
  const [modelUsed, setModelUsed] = useState(null);
  const [weekData, setWeekData] = useState([]);

  const [loading, setLoading] = useState(false);
  const [weekLoading, setWeekLoading] = useState(false);
  const [error, setError] = useState('');

  // Cargar predicciones del día seleccionado
  const loadDay = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [pred, real] = await Promise.all([
        getDemandPrediction(token, selectedDate, { academicWeek, specialEvent }),
        getRealOccupancy(token, selectedDate),
      ]);
      setPredictions(pred.predictions);
      setRealData(real);
      setModelUsed(pred.model_used);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [token, selectedDate, academicWeek, specialEvent]);

  // Cargar heatmap semanal (lunes–sábado de la semana seleccionada)
  const loadWeek = useCallback(async () => {
    setWeekLoading(true);
    try {
      const monday = weekStart(selectedDate);
      const weekPreds = await Promise.all(
        Array.from({ length: 6 }, (_, i) => {
          const d = new Date(monday);
          d.setDate(d.getDate() + i);
          const dateStr = d.toISOString().slice(0, 10);
          return getDemandPrediction(token, dateStr, { academicWeek, specialEvent })
            .catch(() => null);
        })
      );
      setWeekData(weekPreds);
    } catch {
      /* silencioso — heatmap no crítico */
    } finally {
      setWeekLoading(false);
    }
  }, [token, selectedDate, academicWeek, specialEvent]);

  useEffect(() => {
    loadDay();
    loadWeek();
  }, [loadDay, loadWeek]);

  return (
    <div className="page-container">

      {/* Header */}
      <div className="dashboard-welcome animate-in">
        <button
          className="btn btn-secondary"
          onClick={() => navigate('/dashboard')}
          style={{ padding: '0.4rem 0.8rem' }}
        >
          <span className="btn-icon"><IconArrowLeft /></span>
          Volver
        </button>
        <div style={{ flex: 1, marginLeft: '1rem' }}>
          <div style={{ fontWeight: 700, fontSize: 18, color: 'var(--text-primary, #e6edf3)' }}>
            Dashboard de Predicciones
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary, #8b949e)' }}>
            Demanda predicha vs. ocupación real · Ruta Parque
          </div>
        </div>
      </div>

      {/* Controles */}
      <div className="card animate-in" style={{ display: 'flex', flexWrap: 'wrap', gap: 16, padding: '1rem 1.25rem', alignItems: 'flex-end' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <label style={{ fontSize: 12, color: 'var(--text-secondary, #8b949e)' }}>
            <span style={{ marginRight: 6 }}><IconCalendar /></span>Fecha
          </label>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            style={{
              background: 'var(--input-bg, #0d1117)',
              border: '1px solid var(--border, #30363d)',
              color: 'var(--text-primary, #e6edf3)',
              borderRadius: 6,
              padding: '0.4rem 0.7rem',
              fontSize: 13,
            }}
          />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <label style={{ fontSize: 12, color: 'var(--text-secondary, #8b949e)' }}>Semana académica</label>
          <input
            type="number"
            min={1} max={18}
            value={academicWeek}
            onChange={(e) => setAcademicWeek(Number(e.target.value))}
            style={{
              width: 64,
              background: 'var(--input-bg, #0d1117)',
              border: '1px solid var(--border, #30363d)',
              color: 'var(--text-primary, #e6edf3)',
              borderRadius: 6,
              padding: '0.4rem 0.7rem',
              fontSize: 13,
            }}
          />
        </div>

        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-secondary, #8b949e)', cursor: 'pointer', marginBottom: 2 }}>
          <input
            type="checkbox"
            checked={specialEvent}
            onChange={(e) => setSpecialEvent(e.target.checked)}
          />
          Evento especial
        </label>
      </div>

      {error && (
        <div className="alert alert-error animate-in">{error}</div>
      )}

      {/* Métricas del modelo */}
      <div className="section-header animate-in">
        <div className="section-header-icon"><IconCpu /></div>
        <span className="section-header-text">Modelo activo</span>
      </div>
      <div className="animate-in">
        <ModelMetrics modelUsed={modelUsed} />
      </div>

      {/* Gráfico diario */}
      <div className="section-header animate-in" style={{ marginTop: '1.5rem' }}>
        <div className="section-header-icon"><IconCalendar /></div>
        <span className="section-header-text">Demanda por hora — {selectedDate}</span>
      </div>
      <div className="card animate-in" style={{ padding: '1.25rem' }}>
        <DemandChart
          predictions={predictions}
          realData={realData}
          loading={loading}
        />
      </div>

      {/* Heatmap semanal */}
      <div className="section-header animate-in" style={{ marginTop: '1.5rem' }}>
        <div className="section-header-icon"><IconCalendar /></div>
        <span className="section-header-text">Mapa de calor semanal — predicción</span>
      </div>
      <div className="card animate-in" style={{ padding: '1.25rem' }}>
        {weekLoading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '1.5rem' }}>
            <span className="spinner" />
          </div>
        ) : (
          <WeekHeatmap weekData={weekData} />
        )}
      </div>

    </div>
  );
}
