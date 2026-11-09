import { useState } from 'react';
import { firstAuthor } from '../../utils/format';
import styles from './BookCover.module.css';

// Muted cloth-binding colours for books Open Library has no cover for.
const BINDINGS = ['#5b3a32', '#2f4a3f', '#33415c', '#6b4f2a', '#4a3b5c', '#7a2e2a', '#2e4f56'];

function bindingFor(title = '') {
  let hash = 0;
  for (const char of title) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return BINDINGS[hash % BINDINGS.length];
}

/**
 * Real cover from Open Library, or a typeset binding when none exists.
 * `decorative` hides it from screen readers when the title is shown next to it.
 */
export function BookCover({ book, size = 'md', src, className = '', decorative = false }) {
  const [failed, setFailed] = useState(false);
  const url = src ?? book?.cover_image;
  const classes = `${styles.cover} ${styles[size]} ${className}`;

  if (url && !failed) {
    return (
      <div className={classes}>
        <img src={url} alt={decorative ? '' : `Cover of ${book.title}`} loading="lazy" onError={() => setFailed(true)} />
      </div>
    );
  }

  return (
    <div
      className={`${classes} ${styles.fallback}`}
      style={{ background: bindingFor(book?.title) }}
      role={decorative ? undefined : 'img'}
      aria-label={decorative ? undefined : `Cover of ${book?.title}`}
      aria-hidden={decorative || undefined}
    >
      <span className={styles.fallbackTitle} aria-hidden="true">{book?.title}</span>
      <span className={styles.fallbackAuthor} aria-hidden="true">{firstAuthor(book?.author)}</span>
    </div>
  );
}
