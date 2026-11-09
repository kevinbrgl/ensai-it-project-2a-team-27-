import { API_BASE_URL, TOKEN_STORAGE_KEY } from '../config';

/** Error thrown for any failed API call. */
export class ApiError extends Error {
  /**
   * @param {string} message Human readable message
   * @param {number} status HTTP status (0 when the server is unreachable)
   * @param {Record<string, string>} [fieldErrors] Validation errors by field
   */
  constructor(message, status, fieldErrors = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

let unauthorizedHandler = null;

/** Registers the callback run when the session token is rejected. */
export function onUnauthorized(handler) {
  unauthorizedHandler = handler;
}

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_STORAGE_KEY, token);
    else localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // Storage can be unavailable (private mode); the session then lasts one tab.
  }
}

// FastAPI returns either {"detail": "message"} or, for validation errors
// (422), {"detail": [{"loc": [...], "msg": "..."}]}.
function parseErrorBody(body, status) {
  const detail = body && body.detail;
  if (typeof detail === 'string') return { message: detail, fieldErrors: {} };
  if (Array.isArray(detail)) {
    const fieldErrors = {};
    for (const item of detail) {
      const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : 'form';
      const msg = String(item.msg || 'Invalid value').replace(/^Value error, /, '');
      if (!fieldErrors[field]) fieldErrors[field] = msg;
    }
    const first = Object.entries(fieldErrors)[0];
    return {
      message: first ? `${first[0]}: ${first[1]}` : 'Some fields are invalid.',
      fieldErrors,
    };
  }
  return { message: defaultMessage(status), fieldErrors: {} };
}

function defaultMessage(status) {
  if (status >= 500) return 'The server ran into a problem. Please try again.';
  if (status === 404) return 'Not found.';
  if (status === 403) return 'You are not allowed to do this.';
  return `Request failed (${status}).`;
}

// The backend answers 403 "Could not validate credentials" for expired or
// revoked tokens, and 404 "No such user in database" if the account is gone.
function isSessionError(status, message) {
  return (
    (status === 403 && message === 'Could not validate credentials') ||
    (status === 401 && message === 'Not authenticated') ||
    (status === 404 && message === 'No such user in database')
  );
}

/**
 * Sends a request to the backend.
 *
 * @param {string} path Path relative to the API root, e.g. "/books/search"
 * @param {object} [options]
 * @param {string} [options.method]
 * @param {object} [options.query] Query string parameters (empty values skipped)
 * @param {object} [options.json] JSON body
 * @param {URLSearchParams} [options.form] Form-encoded body
 * @param {AbortSignal} [options.signal]
 * @returns {Promise<any>} Parsed JSON, or null for empty responses
 */
export async function request(path, { method = 'GET', query, json, form, signal } = {}) {
  let url = `${API_BASE_URL}${path}`;
  if (query) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== '') params.append(key, String(value));
    }
    const qs = params.toString();
    if (qs) url += `?${qs}`;
  }

  const headers = { Accept: 'application/json' };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let body;
  if (json !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(json);
  } else if (form) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded';
    body = form.toString();
  }

  let response;
  try {
    response = await fetch(url, { method, headers, body, signal });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new ApiError('Cannot reach the server. Check that the backend is running.', 0);
  }

  if (response.status === 204) return null;

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    const { message, fieldErrors } = parseErrorBody(data, response.status);
    if (token && isSessionError(response.status, message) && unauthorizedHandler) {
      unauthorizedHandler();
    }
    throw new ApiError(message, response.status, fieldErrors);
  }
  return data;
}
