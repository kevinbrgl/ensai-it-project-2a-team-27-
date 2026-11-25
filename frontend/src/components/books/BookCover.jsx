import { useState } from 'react';
import { firstAuthor } from '../../utils/format';
import styles from './BookCover.module.css';

// Muted cloth-binding colors for books Open Library has no cover for.
const BINDINGS = ['#5b3a32', '#2f4a3f', '#33415c', '#6b4f2a', '#4a3b5c', '#7a2e2a', '#2e4f56'];
const OPEN_LIBRARY_COVER = /^(https:\/\/covers\.openlibrary\.org\/b\/id\/\d+)-([SML])\.jpg$/;

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
  const [image, setImage] = useState(null);
  const url = (src ?? book?.cover_image)?.replace(OPEN_LIBRARY_COVER, (_, base, variant) => (
    `${base}-${size === 'sm' && !src ? 'S' : variant}.jpg?default=false`
  ));
  const status = image && image.url === url ? image.status : 'loading';
  const loaded = status === 'loaded';
  const classes = `${styles.cover} ${styles[size]} ${loaded ? '' : styles.fallback} ${className}`;

  return (
    <div
      className={classes}
      style={loaded ? undefined : { background: bindingFor(book?.title) }}
      role={decorative ? undefined : 'img'}
      aria-label={decorative ? undefined : `Cover of ${book?.title}`}
      aria-hidden={decorative || undefined}
    >
      {!loaded && (
        <>
          <span className={styles.fallbackTitle} aria-hidden="true">{book?.title}</span>
          <span className={styles.fallbackAuthor} aria-hidden="true">{firstAuthor(book?.author)}</span>
        </>
      )}
      {url && status !== 'failed' && (
        <img
          key={url}
          className={loaded ? undefined : styles.loading}
          alt=""
          loading={size === 'lg' ? 'eager' : 'lazy'}
          decoding="async"
          onLoad={() => setImage({ url, status: 'loaded' })}
          onError={() => setImage({ url, status: 'failed' })}
          src={url}
        />
      )}
    </div>
  );
}
