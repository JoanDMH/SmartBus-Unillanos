import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getRoutes, getTripStats, getDemandAnalysis } from '../api/tripApi';

/* ─── Inline SVG Icons ─── */
const IconBus = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M8 6v6"/><path d="M15 6v6"/><path d="M2 12h19.6"/><path d="M18 18h3s.5-1.7.8-2.8c.1-.4.2-.8.2-1.2 0-.4-.1-.8-.2-1.2l-1.4-5C20.1 6.8 19.1 6 18 6H6c-1.1 0-2.1.8-2.4 1.8l-1.4 5c-.1.4-.2.8-.2 1.2 0 .4.1.8.2 1.2C2.7 16.3 3.2 18 3.2 18H6"/>
    <circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>
  </svg>
);

const IconPlus = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 12h14"/><path d="M12 5v14"/>
  </svg>
);

const IconList = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/>
    <line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>
  </svg>
);

const IconLogout = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
  </svg>
);

const IconTrips = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
  </svg>
);

const IconUsers = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
    <path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
);

const IconTrendUp = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>
  </svg>
);

const IconClock = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
  </svg>
);

const IconRoute = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>
  </svg>
);

const IconSparkles = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
    <path d="M5 3v4"/><path d="M19 17v4"/><path d="M3 5h4"/><path d="M17 19h4"/>
  </svg>
);

export default function DashboardPage() {
  const { token, user, logout } = useAuth();
  const navigate = useNavigate();

  const [routes, setRoutes] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  // AI analysis state
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const [r, s] = await Promise.all([
          getRoutes(),
          getTripStats(token),
        ]);
        setRoutes(r);
        setStats(s);
      } catch {
        /* silent — stats will show zeros */
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [token]);

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  const handleAiAnalysis = async () => {
    setAiLoading(true);
    setAiError('');
    setAiAnalysis(null);
    try {
      const data = await getDemandAnalysis(token);
      setAiAnalysis(data.analysis);
    } catch (err) {
      setAiError(err.message);
    } finally {
      setAiLoading(false);
    }
  };

  const userInitial = user ? user.charAt(0).toUpperCase() : '?';

  return (
    <div className="page-container">
      {/* Welcome Bar */}
      <div className="dashboard-welcome animate-in">
        <div className="welcome-avatar">{userInitial}</div>
        <div className="welcome-info">
          <div className="welcome-greeting">Bienvenido de vuelta</div>
          <div className="welcome-name">{user || 'Usuario'}</div>
        </div>
        <div className="nav-actions">
          <button className="btn btn-primary" onClick={() => navigate('/trips/new')}>
            <span className="btn-icon"><IconPlus /></span>
            Registrar Viaje
          </button>
          <button className="btn btn-secondary" onClick={() => navigate('/trips')}>
            <span className="btn-icon"><IconList /></span>
            Historial
          </button>
          <button className="btn btn-secondary" onClick={() => navigate('/predictions')}>
            <span className="btn-icon"><IconSparkles /></span>
            Predicciones IA
          </button>
          <button className="btn btn-secondary" onClick={() => navigate('/schedule')}>
            <span className="btn-icon"><IconClock /></span>
            Horarios
          </button>
          <button className="btn btn-danger" onClick={handleLogout}>
            <span className="btn-icon"><IconLogout /></span>
            Salir
          </button>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem' }}>
          <span className="spinner" />
        </div>
      ) : (
        <>
          {/* Stats */}
          <div className="section-header animate-in">
            <div className="section-header-icon"><IconTrendUp /></div>
            <span className="section-header-text">Resumen de operación</span>
          </div>

          <div className="stats-grid">
            <div className="card stat-card animate-in">
              <div className="stat-icon"><IconTrips /></div>
              <div className="stat-value">{stats?.total_trips ?? 0}</div>
              <div className="stat-label">Viajes registrados</div>
            </div>
            <div className="card stat-card animate-in">
              <div className="stat-icon"><IconUsers /></div>
              <div className="stat-value">{stats?.average_passengers ?? 0}</div>
              <div className="stat-label">Pasajeros promedio</div>
            </div>
            <div className="card stat-card animate-in">
              <div className="stat-icon"><IconTrendUp /></div>
              <div className="stat-value">{stats?.max_passengers ?? 0}</div>
              <div className="stat-label">Máx. pasajeros</div>
            </div>
            <div className="card stat-card animate-in">
              <div className="stat-icon"><IconClock /></div>
              <div className="stat-value">{stats?.busiest_hour ?? '—'}</div>
              <div className="stat-label">Hora pico</div>
            </div>
          </div>

          {/* AI Analysis Section */}
          <div className="section-header animate-in">
            <div className="section-header-icon ai-icon"><IconSparkles /></div>
            <span className="section-header-text">Análisis Inteligente</span>
          </div>

          <div className="ai-card card animate-in">
            <div className="ai-card-header">
              <div className="ai-card-badge">
                <IconSparkles />
                <span>IA · Groq</span>
              </div>
              <p className="ai-card-desc">
                Análisis de patrones de demanda generado por inteligencia artificial
                a partir de los viajes registrados en la base de datos.
              </p>
            </div>

            {aiAnalysis && (
              <div className="ai-card-content">
                <p className="ai-card-text">{aiAnalysis}</p>
              </div>
            )}

            {aiError && (
              <div className="alert alert-error" style={{ marginTop: '1rem' }}>
                {aiError}
              </div>
            )}

            <button
              className="btn btn-ai"
              onClick={handleAiAnalysis}
              disabled={aiLoading}
            >
              {aiLoading ? (
                <>
                  <span className="spinner" />
                  Analizando…
                </>
              ) : (
                <>
                  <span className="btn-icon"><IconSparkles /></span>
                  {aiAnalysis ? 'Generar nuevo análisis' : 'Generar análisis de demanda'}
                </>
              )}
            </button>
          </div>

          {/* Route Cards */}
          <div className="section-header animate-in">
            <div className="section-header-icon"><IconRoute /></div>
            <span className="section-header-text">Rutas disponibles</span>
          </div>

          {routes.map((route) => (
            <div key={route.id} className="route-card-wrapper animate-in">
              <div className="card route-card">
                <div className="route-card-header">
                  <div className="route-card-icon">
                    <IconBus />
                  </div>
                  <div className="route-card-info">
                    <div className="route-card-name">{route.name}</div>
                    <div className="route-card-desc">{route.description}</div>
                  </div>
                  <div className="route-card-badge">
                    <span className="route-card-badge-dot" />
                    Activa
                  </div>
                </div>

                <div className="route-card-divider" />

                <div className="route-card-schedule-header">
                  <span className="route-card-schedule-title">Horarios de salida</span>
                  <span className="route-card-schedule-count">{route.schedule.length} salidas</span>
                </div>

                <div className="schedule-list">
                  {route.schedule.map((time) => (
                    <span key={time} className="schedule-pill">{time}</span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
