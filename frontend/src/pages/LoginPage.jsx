import { useState } from 'react';
import { useNavigate, Navigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { loginUser } from '../api/authApi';

const IconBus = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="url(#busGrad)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <defs>
      <linearGradient id="busGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#6366f1" />
        <stop offset="100%" stopColor="#06b6d4" />
      </linearGradient>
    </defs>
    <path d="M8 6v6"/><path d="M15 6v6"/><path d="M2 12h19.6"/><path d="M18 18h3s.5-1.7.8-2.8c.1-.4.2-.8.2-1.2 0-.4-.1-.8-.2-1.2l-1.4-5C20.1 6.8 19.1 6 18 6H6c-1.1 0-2.1.8-2.4 1.8l-1.4 5c-.1.4-.2.8-.2 1.2 0 .4.1.8.2 1.2C2.7 16.3 3.2 18 3.2 18H6"/>
    <circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>
  </svg>
);

export default function LoginPage() {
  const { token, login } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({ usernameOrEmail: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Already authenticated → go to dashboard
  if (token) return <Navigate to="/dashboard" replace />;

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const { token: jwt } = await loginUser(form.usernameOrEmail, form.password);
      login(jwt);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-wrapper">
      <form className="card login-card animate-in" onSubmit={handleSubmit}>
        <div className="login-logo">
          <IconBus />
          SmartBus
        </div>
        <p className="login-tagline">Universidad de los Llanos — Ruta Parque</p>

        {error && <div className="alert alert-error">{error}</div>}

        <div className="form-group">
          <label className="form-label" htmlFor="usernameOrEmail">
            Usuario o correo
          </label>
          <input
            id="usernameOrEmail"
            name="usernameOrEmail"
            className="form-input"
            type="text"
            placeholder="nombre de usuario o email"
            value={form.usernameOrEmail}
            onChange={handleChange}
            required
            autoFocus
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="password">
            Contraseña
          </label>
          <input
            id="password"
            name="password"
            className="form-input"
            type="password"
            placeholder="••••••••"
            value={form.password}
            onChange={handleChange}
            required
          />
        </div>

        <button
          type="submit"
          className="btn btn-primary btn-block"
          disabled={loading}
        >
          {loading ? <span className="spinner" /> : 'Iniciar Sesión'}
        </button>

        <p style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          ¿No tienes cuenta?{' '}
          <Link to="/register" style={{ color: 'var(--accent-primary-hover)' }}>
            Crear cuenta
          </Link>
        </p>
      </form>
    </div>
  );
}
