export const STATUS_LABELS = {
  WANT_TO_READ: 'Want to read',
  READING: 'Reading',
  COMPLETED: 'Finished',
};

/** Year of a "YYYY-MM-DD" date, or null. */
export function yearOf(date) {
  if (!date) return null;
  const year = Number(String(date).slice(0, 4));
  return Number.isFinite(year) && year > 0 ? year : null;
}

const dateFormatter = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

export function formatDate(value) {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '' : dateFormatter.format(date);
}

/** Formats a 0–5 rating with one decimal, e.g. 4.2. */
export function formatRating(value) {
  return typeof value === 'number' ? value.toFixed(1) : '–';
}

export function plural(count, word, pluralWord = `${word}s`) {
  return `${count} ${count === 1 ? word : pluralWord}`;
}

/** Open Library covers come in S/M/L sizes; use the large one for big displays. */
export function largeCover(url) {
  return url ? url.replace(/-M\.jpg$/, '-L.jpg') : url;
}

/** Only the first author is shown in compact layouts. */
export function firstAuthor(author) {
  if (!author) return 'Unknown author';
  return author.split(',')[0].trim();
}

export function greeting(date = new Date()) {
  const hour = date.getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}
