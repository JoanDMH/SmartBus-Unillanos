// Uses env var in production builds, falls back to /api for local dev (Vite proxy)
const AUTH_BASE = import.meta.env.VITE_AUTH_BASE_URL || '/api';

/**
 * Register a new user via MiniIdentity API.
 * Roles are assigned separately by an administrator after registration.
 * @param {string} username
 * @param {string} email
 * @param {string} password
 * @returns {Promise<void>}
 */
export async function registerUser(username, email, password) {
  const res = await fetch(`${AUTH_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      body.detail || body.message || body.title || 'Error al registrar el usuario'
    );
  }
}

/**
 * Login via MiniIdentity API.
 * @param {string} usernameOrEmail
 * @param {string} password
 * @returns {Promise<{token: string}>}
 */
export async function loginUser(usernameOrEmail, password) {
  const res = await fetch(`${AUTH_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ usernameOrEmail, password }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || body.message || 'Error de autenticación');
  }

  const data = await res.json();
  // MiniIdentity returns { accessToken, tokenType, username, ... }
  // Normalize to { token } for the rest of the frontend
  return { token: data.accessToken || data.token };
}
