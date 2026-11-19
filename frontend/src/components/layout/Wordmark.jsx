import styles from './Wordmark.module.css';

export function Wordmark() {
  return (
    <span className={styles.wordmark}>
      <svg viewBox="0 0 40 36" fill="none" aria-hidden="true">
        <g stroke="currentColor" strokeWidth="1.65" strokeLinejoin="round" strokeLinecap="round">
          <path d="m3 12 17 8 17-8v13l-17 8-17-8z" />
          <path d="m6 8 14 7 14-7M10 4l10 5 10-5M20 20v13" />
        </g>
      </svg>
      Ex-Libris
    </span>
  );
}
