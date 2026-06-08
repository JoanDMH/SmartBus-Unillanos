/**
 * DEV-D2 — ScheduleApprovalPage
 * Módulo de gobernanza de horarios (human-in-the-loop).
 *
 * Flujo:
 *   1. El despachador indica la semana y la configuración de flota.
 *   2. "Generar grilla" llama a POST /trips/optimization/weekly-schedule.
 *   3. El resultado se muestra en WeeklyScheduleTable con inputs editables.
 *   4. "Confirmar grilla" llama a POST .../approve y persiste la versión aprobada.
 *   5. La sección inferior muestra el último itinerario aprobado (read-only).
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import WeeklyScheduleTable from '../components/WeeklyScheduleTable';
import {
  generateWeeklySchedule,
  approveSchedule,
  getLatestApprovedSchedule,
} from '../api/optimizationApi';

/* ── Helpers ─────────────────────────────────────────────────────────────── */

function currentWeekLabel() {
  const now = new Date();
  const jan4 = new Date(now.getFullYear(), 0, 4);
  const weekNum = Math.ceil((((now - jan4) / 86400000) + jan4.getDay() + 1) / 7);
  return `${now.getFullYear()}-W${String(weekNum).padStart(2, '0')}`;
}

function formatCOP(value) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(value);
}

/* ── Icons ───────────────────────────────────────────────────────────────── */

const IconArrowLeft = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="15 18 9 12 15 6" />
  </svg>
);

const IconCheck = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

const IconRefresh = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" />
    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
  </svg>
);

/* ── Página ──────────────────────────────────────────────────────────────── */

export default function ScheduleApprovalPage() {
  const { token } = useAuth();
  const navigate = useNavigate();

  // Formulario de generación
  const [weekLabel, setWeekLabel] = useState(currentWeekLabel());
  const [academicWeek, setAcademicWeek] = useState(1);
  const [specialEvent, setSpecialEvent] = useState(false);
  const [availableBuses, setAvailableBuses] = useState(3);
  const [availableDrivers, setAvailableDrivers] = useState(6);

  // Estado de la grilla pendiente
  const [pendingSchedule, setPendingSchedule] = useState(null);
  const [editedSchedule, setEditedSchedule] = useState(null);  // copia editable

  // Estado del último aprobado
  const [approvedSchedule, setApprovedSchedule] = useState(null);
  const [approvedLoading, setApprovedLoading] = useState(true);

  const [generating, setGenerating] = useState(false);
  const [approving, setApproving] = useState(false);
  const [generateError, setGenerateError] = useState('');
  const [approveError, setApproveError] = useState('');
  const [approveSuccess, setApproveSuccess] = useState('');

  // Cargar el último itinerario aprobado al montar
  const loadApproved = useCallback(async () => {
    setApprovedLoading(true);
    try {
      const data = await getLatestApprovedSchedule(token);
      setApprovedSchedule(data);
    } catch {
      setApprovedSchedule(null);
    } finally {
      setApprovedLoading(false);
    }
  }, [token]);

  useEffect(() => { loadApproved(); }, [loadApproved]);

  // Generar nueva grilla
  const handleGenerate = async () => {
    setGenerating(true);
    setGenerateError('');
    setPendingSchedule(null);
    setEditedSchedule(null);
    setApproveSuccess('');
    try {
      const result = await generateWeeklySchedule(token, {
        week_label: weekLabel,
        academic_week: academicWeek,
        special_event: specialEvent,
        fleet: { available_buses: availableBuses, available_drivers: availableDrivers, bus_type: 'estandar' },
      });
      setPendingSchedule(result);
      // Copia profunda para edición
      setEditedSchedule(JSON.parse(JSON.stringify(result.schedule_by_day)));
    } catch (err) {
      setGenerateError(err.message);
    } finally {
      setGenerating(false);
    }
  };

  // Edición manual de buses en la tabla
  const handleEdit = (day, hour, newBuses) => {
    setEditedSchedule((prev) => {
      const updated = { ...prev };
      updated[day] = updated[day].map((entry) =>
        entry.hour === hour
          ? { ...entry, buses_dispatched: newBuses, passengers_covered: newBuses * 40 }
          : entry
      );
      return updated;
    });
  };

  // Calcular costo total de la grilla editada
  const editedTotalCost = editedSchedule
    ? Object.values(editedSchedule).flat().reduce((s, e) => s + (e.cost_cop || 0), 0)
    : 0;

  // Aprobar la grilla
  const handleApprove = async () => {
    if (!pendingSchedule) return;
    setApproving(true);
    setApproveError('');
    setApproveSuccess('');
    try {
      await approveSchedule(token, pendingSchedule.id);
      setApproveSuccess(`Grilla semana ${pendingSchedule.week_label} aprobada.`);
      setPendingSchedule(null);
      setEditedSchedule(null);
      await loadApproved();
    } catch (err) {
      setApproveError(err.message);
    } finally {
      setApproving(false);
    }
  };

  return (
    <div className="page-container">

      {/* Header */}
      <div className="dashboard-welcome animate-in">
        <button className="btn btn-secondary" onClick={() => navigate('/dashboard')} style={{ padding: '0.4rem 0.8rem' }}>
          <span className="btn-icon"><IconArrowLeft /></span>
          Volver
        </button>
        <div style={{ flex: 1, marginLeft: '1rem' }}>
          <div style={{ fontWeight: 700, fontSize: 18, color: 'var(--text-primary, #e6edf3)' }}>
            Aprobación de Itinerario Semanal
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary, #8b949e)' }}>
            Revisa y aprueba la grilla generada por el optimizador antes de publicarla
          </div>
        </div>
      </div>

      {/* ── Formulario de generación ── */}
      <div className="section-header animate-in">
        <span className="section-header-text">1 · Configurar y generar grilla</span>
      </div>

      <div className="card animate-in" style={{ padding: '1.25rem', display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'flex-end' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <label style={{ fontSize: 12, color: 'var(--text-secondary, #8b949e)' }}>Semana (ISO)</label>
          <input
            type="week"
            value={weekLabel.replace('W', 'W')}
            onChange={(e) => setWeekLabel(e.target.value.replace('W', 'W'))}
            style={inputStyle}
          />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <label style={{ fontSize: 12, color: 'var(--text-secondary, #8b949e)' }}>Semana académica</label>
          <input type="number" min={1} max={18} value={academicWeek} onChange={(e) => setAcademicWeek(Number(e.target.value))} style={{ ...inputStyle, width: 64 }} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <label style={{ fontSize: 12, color: 'var(--text-secondary, #8b949e)' }}>Buses disponibles</label>
          <input type="number" min={1} max={10} value={availableBuses} onChange={(e) => setAvailableBuses(Number(e.target.value))} style={{ ...inputStyle, width: 64 }} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <label style={{ fontSize: 12, color: 'var(--text-secondary, #8b949e)' }}>Conductores disponibles</label>
          <input type="number" min={1} max={20} value={availableDrivers} onChange={(e) => setAvailableDrivers(Number(e.target.value))} style={{ ...inputStyle, width: 64 }} />
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-secondary, #8b949e)', cursor: 'pointer', marginBottom: 2 }}>
          <input type="checkbox" checked={specialEvent} onChange={(e) => setSpecialEvent(e.target.checked)} />
          Evento especial
        </label>

        <button className="btn btn-primary" onClick={handleGenerate} disabled={generating} style={{ marginLeft: 'auto' }}>
          {generating ? <><span className="spinner" /> Generando…</> : <><span className="btn-icon"><IconRefresh /></span>Generar grilla</>}
        </button>
      </div>

      {generateError && <div className="alert alert-error animate-in">{generateError}</div>}

      {/* ── Revisión y edición ── */}
      {editedSchedule && pendingSchedule && (
        <>
          <div className="section-header animate-in" style={{ marginTop: '1.5rem' }}>
            <span className="section-header-text">2 · Revisar y ajustar manualmente</span>
          </div>

          {pendingSchedule.solver_message && (
            <div className="alert" style={{ background: '#2d1a00', border: '1px solid #9e6a03', color: '#e3b341', borderRadius: 8, padding: '0.75rem 1rem', marginBottom: '1rem', fontSize: 13 }}>
              ⚠ {pendingSchedule.solver_message}
            </div>
          )}

          <div className="card animate-in" style={{ padding: '1.25rem' }}>
            <WeeklyScheduleTable
              scheduleByDay={editedSchedule}
              onEdit={handleEdit}
              readOnly={false}
            />
          </div>

          {/* Resumen de costo */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 16, margin: '1rem 0' }}>
            <span style={{ fontSize: 13, color: 'var(--text-secondary, #8b949e)' }}>
              Costo semanal estimado:
            </span>
            <span style={{ fontWeight: 700, fontSize: 16, color: '#e6edf3' }}>
              {formatCOP(editedTotalCost)}
            </span>
          </div>

          {/* ── Confirmación ── */}
          <div className="section-header animate-in">
            <span className="section-header-text">3 · Aprobar y publicar</span>
          </div>

          <div className="card animate-in" style={{ padding: '1.25rem', display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
            <p style={{ flex: 1, fontSize: 13, color: 'var(--text-secondary, #8b949e)', margin: 0 }}>
              Al confirmar, el itinerario quedará disponible para los conductores y el sistema de monitoreo. Esta acción no se puede deshacer.
            </p>
            <button className="btn btn-primary" onClick={handleApprove} disabled={approving} style={{ background: '#238636', borderColor: '#2ea043' }}>
              {approving
                ? <><span className="spinner" /> Aprobando…</>
                : <><span className="btn-icon"><IconCheck /></span>Confirmar grilla</>}
            </button>
          </div>

          {approveError && <div className="alert alert-error animate-in">{approveError}</div>}
        </>
      )}

      {approveSuccess && (
        <div className="alert animate-in" style={{ background: '#0d2d1f', border: '1px solid #238636', color: '#3fb950', borderRadius: 8, padding: '0.75rem 1rem', fontSize: 13 }}>
          ✓ {approveSuccess}
        </div>
      )}

      {/* ── Último itinerario aprobado ── */}
      <div className="section-header animate-in" style={{ marginTop: '2rem' }}>
        <span className="section-header-text">Último itinerario aprobado</span>
      </div>

      <div className="card animate-in" style={{ padding: '1.25rem' }}>
        {approvedLoading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '1.5rem' }}><span className="spinner" /></div>
        ) : approvedSchedule ? (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
              <div style={{ fontSize: 13 }}>
                <span style={{ color: 'var(--text-secondary, #8b949e)' }}>Semana: </span>
                <strong style={{ color: '#e6edf3' }}>{approvedSchedule.week_label}</strong>
                <span style={{ marginLeft: 16, color: 'var(--text-secondary, #8b949e)' }}>Aprobado por: </span>
                <strong style={{ color: '#3fb950' }}>{approvedSchedule.approved_by}</strong>
              </div>
              <span style={{ fontSize: 12, color: 'var(--text-secondary, #8b949e)' }}>
                Costo: {formatCOP(approvedSchedule.total_cost_cop)}
              </span>
            </div>
            <WeeklyScheduleTable
              scheduleByDay={approvedSchedule.schedule_by_day}
              readOnly={true}
            />
          </>
        ) : (
          <p style={{ color: 'var(--text-secondary, #8b949e)', fontSize: 14 }}>
            No hay itinerarios aprobados aún. Genera y aprueba uno usando el formulario de arriba.
          </p>
        )}
      </div>

    </div>
  );
}

const inputStyle = {
  background: 'var(--input-bg, #0d1117)',
  border: '1px solid var(--border, #30363d)',
  color: 'var(--text-primary, #e6edf3)',
  borderRadius: 6,
  padding: '0.4rem 0.7rem',
  fontSize: 13,
};
