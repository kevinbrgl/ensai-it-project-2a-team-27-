import { useState } from 'react';
import { Icon } from './Icon';
import styles from './StarRating.module.css';

const LABELS = ['', 'Disappointing', 'Okay', 'Good', 'Very good', 'Outstanding'];

/** Read-only stars for a 0–5 value. */
export function Stars({ value = 0, size = 14 }) {
  const rounded = Math.round(value);
  return (
    <span className={styles.stars} aria-label={`${value} out of 5`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <Icon key={n} name="star" size={size} filled={n <= rounded} className={n <= rounded ? styles.on : styles.off} />
      ))}
    </span>
  );
}

/** Interactive 1–5 rating input. */
export function StarInput({ value, onChange, error }) {
  const [hover, setHover] = useState(0);
  const shown = hover || value;
  return (
    <div className={styles.inputRow}>
      <div className={styles.input} role="radiogroup" aria-label="Rating" onMouseLeave={() => setHover(0)}>
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            role="radio"
            aria-checked={value === n}
            aria-label={`${n} star${n > 1 ? 's' : ''}`}
            className={styles.starButton}
            onMouseEnter={() => setHover(n)}
            onClick={() => onChange(n)}
          >
            <Icon name="star" size={26} filled={n <= shown} className={n <= shown ? styles.on : styles.off} />
          </button>
        ))}
      </div>
      <span className={error ? styles.error : styles.label}>{error || LABELS[shown] || 'Select a rating'}</span>
    </div>
  );
}
