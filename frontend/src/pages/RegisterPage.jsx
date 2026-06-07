import { useState } from 'react';
import { useNavigate, Navigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { registerUser } from '../api/authApi';

const IconBus = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="url(#busGradReg)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <defs>
      <linearGradient id="busGradReg" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#6366f1" />
        <stop offset="100%" stopColor="#06b6d4" />
      </linearGradient>
    </defs>
    <path d="M8 6v6"/><path d="M15 6v6"/><path d="M2 12h19.6"/><path d="M18 18h3s.5-1.7.8-2.8c.1-.4.2-.8.2-1.2 0-.4-.1-.8-.2-1.2l-1.4-5C20.1 6.8 19.1 6 18 6H6c-1.1 0-2.1.8-2.4 1.8l-1.4 5c-.1.4-.2.8-.2 1.2 0 .4.1.8.2 1.2C2.7 16.3 3.2 18 3.2 18H6"/>
    <circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>
  </svg>
);

const IconCheck = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);

const PASSWORD_RULES = [
  { test: (p) => p.length >= 8,           label: 'Mínimo 8 caracteres' },
  { test: (p) => /[A-Z]/.test(p),         label: 'Al menos una mayúscula' },
  { test: (p) => /[0-9]/.test(p),         label: 'Al menos un número' },
  { test: (p) => /[^A-Za-z0-9]/.test(p), label: 'Al menos un carácter especial (!@#...)' },
];

export default function RegisterPage() {
  const { token } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({ username: '', email: '', password: '', confirm: '' });
  const [error, setError]     = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  if (token) return <Navigate to="/dashboard" replace />;

  const handleChange = (e) =>
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (form.password !== form.confirm) {
      setError('Las contraseñas no coinciden.');
      return;
    }
    const failedRule = PASSWORD_RULES.find((r) => !r.test(form.password));
    if (failedRule) {
      setError(`La contraseña no cumple: ${failedRule.label.toLowerCase()}.`);
      return;
    }

    setLoading(true);
    try {
      await registerUser(form.username, form.email, form.password);
      setSuccess(true);
      setTimeout(() => navigate('/login', { replace: true }), 2500);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-wrapper">
      <form className="card login-card animate-in" onSubmit={handleSubmit} style={{ maxWidth: 440 }}>
        <div className="login-logo">
          <IconBus />
          SmartBus
        </div>
        <p className="login-tagline">Crear cuenta — Universidad de los Llanos</p>

        {error && <div className="alert alert-error">{error}</div>}

        {success ? (
          <div className="alert alert-success" style={{ textAlign: 'center' }}>
            Cuenta creada correctamente. Redirigiendo al login...
          </div>
        ) : (
          <>
            <div className="form-group">
              <label className="form-label" htmlFor="username">Nombre de usuario</label>
              <input
                id="username" name="username" className="form-input" type="text"
                placeholder="ej. juan.conductor" value={form.username}
                onChange={handleChange} required autoFocus
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="email">Correo electrónico</label>
              <input
                id="email" name="email" className="form-input" type="email"
                placeholder="usuario@unillanos.edu.co" value={form.email}
                onChange={handleChange} required
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="password">Contraseña</label>
              <input
                id="password" name="password" className="form-input" type="password"
                placeholder="••••••••" value={form.password}
                onChange={handleChange} required
              />
              {/* Password strength checklist */}
              {form.password.length > 0 && (
                <ul style={{ listStyle: 'none', marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  {PASSWORD_RULES.map((rule) => (
                    <li key={rule.label} style={{
                      fontSize: '0.75rem',
                      display: 'flex', alignItems: 'center', gap: '0.4rem',
                      color: rule.test(form.password) ? 'var(--accent-success)' : 'var(--text-muted)',
                      transition: 'color 200ms',
                    }}>
                      <IconCheck />
                      {rule.label}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="confirm">Confirmar contraseña</label>
              <input
                id="confirm" name="confirm" className="form-input" type="password"
                placeholder="••••••••" value={form.confirm}
                onChange={handleChange} required
              />
            </div>

            <div className="alert" style={{
              background: 'rgba(99,102,241,0.07)',
              border: '1px solid rgba(99,102,241,0.18)',
              color: 'var(--text-secondary)',
              fontSize: '0.8rem',
              marginBottom: '1rem',
            }}>
              El rol (conductor, despachador, administrador) será asignado por un administrador una vez creada la cuenta.
            </div>

            <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
              {loading ? <span className="spinner" /> : 'Crear cuenta'}
            </button>
          </>
        )}

        <p style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          ¿Ya tienes cuenta?{' '}
          <Link to="/login" style={{ color: 'var(--accent-primary-hover)' }}>
            Iniciar sesión
          </Link>
        </p>
      </form>
    </div>
  );
}
