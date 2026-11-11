const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Rules mirror the backend Pydantic models (src/models/users.py).
export function validateUsername(value) {
  const v = value.trim();
  if (!v) return 'Choose a username.';
  if (v.length < 3) return 'At least 3 characters.';
  if (v.length > 30) return 'At most 30 characters.';
  return null;
}

export function validateEmail(value) {
  if (!value.trim()) return 'Enter your email address.';
  if (!EMAIL_RE.test(value.trim())) return 'This email address looks incomplete.';
  return null;
}

export function validatePassword(value) {
  if (!value) return 'Enter a password.';
  if (value.length < 8) return 'At least 8 characters.';
  if (value.length > 72) return 'At most 72 characters.';
  return null;
}

export function validateUrl(value) {
  if (!value.trim()) return null;
  try {
    const url = new URL(value.trim());
    return url.protocol === 'http:' || url.protocol === 'https:' ? null : 'Use an http(s) link.';
  } catch {
    return 'Enter a full link, starting with https://';
  }
}

/** Runs validators and returns only the failing fields. */
export function collectErrors(checks) {
  const errors = {};
  for (const [field, message] of Object.entries(checks)) if (message) errors[field] = message;
  return errors;
}
