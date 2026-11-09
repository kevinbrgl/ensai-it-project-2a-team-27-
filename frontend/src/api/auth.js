import { request } from './client';

/** POST /auth/register → UserRead */
export function register({ username, email, password }) {
  return request('/auth/register', { method: 'POST', json: { username, email, password } });
}

/** POST /auth/login (OAuth2 form) → { access_token, token_type } */
export function login({ username, password }) {
  const form = new URLSearchParams({ username, password });
  return request('/auth/login', { method: 'POST', form });
}

/** POST /auth/logout → 204, revokes the current token */
export function logout() {
  return request('/auth/logout', { method: 'POST' });
}
