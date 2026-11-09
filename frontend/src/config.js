/**
 * Runtime configuration read from Vite environment variables.
 * See `.env.example` for the full list.
 */
const explicitApiUrl = (import.meta.env.VITE_API_URL || '').trim();

/**
 * Path the app is served under, e.g. "/" or "/proxy/5173/".
 * In development it comes from VITE_BASE_PATH; in the built app it is
 * detected from the URL by the small script in index.html.
 */
export const APP_BASE = import.meta.env.DEV ? import.meta.env.BASE_URL : window.__EXLIBRIS_BASE__ || '/';

/** Base URL of the backend API, without trailing slash (e.g. "/api"). */
export const API_BASE_URL = (explicitApiUrl || `${APP_BASE}api`).replace(/\/$/, '');

/** Key used to persist the access token in localStorage. */
export const TOKEN_STORAGE_KEY = 'exlibris.token';
