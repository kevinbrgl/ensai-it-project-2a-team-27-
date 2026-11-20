import { useState } from 'react';
import { formatRating, plural } from '../../utils/format';
import { genreInk } from '../../utils/genreWheel';
import { Avatar } from '../ui/Avatar';
import { Skeleton } from '../ui/Skeleton';
import { EmptyState, ErrorState } from '../ui/States';
import styles from './GenreWheel.module.css';

// Two arcs per edge also draw a complete ring when one genre has a 100% share.
function ringSegment(start, end) {
  function point(percent, radius) {
    const angle = (percent / 100) * Math.PI * 2 - Math.PI / 2;
    return `${100 + radius * Math.cos(angle)},${100 + radius * Math.sin(angle)}`;
  }
  const mid = (start + end) / 2;
  return [
    `M ${point(start, 78)}`,
    `A 78 78 0 0 1 ${point(mid, 78)}`,
    `A 78 78 0 0 1 ${point(end, 78)}`,
    `L ${point(end, 51)}`,
    `A 51 51 0 0 0 ${point(mid, 51)}`,
    `A 51 51 0 0 0 ${point(start, 51)} Z`,
  ].join(' ');
}

function WheelChart({ wheel, user }) {
  const [selectedGenre, setSelectedGenre] = useState('');
  const segments = wheel.segments;
  const selected = segments.find((segment) => segment.genre === selectedGenre) ?? segments[0];
  const empty = wheel.is_empty || !selected;
  let end = 0;
  const arcs = segments.map((segment) => {
    const start = end;
    end += segment.percentage;
    return { segment, path: ringSegment(start, end) };
  });

  return (
    <figure className={styles.figure}>
      <div className={styles.chart}>
        <svg viewBox="0 0 200 200" aria-hidden="true" focusable="false">
          <g className={styles.guides} fill="none">
            <circle cx="100" cy="100" r="93" />
            <circle cx="100" cy="100" r="87" pathLength="100" strokeDasharray=".22 1.78" strokeWidth="3" />
            <circle cx="100" cy="100" r="46" />
          </g>
          {empty ? (
            <circle cx="100" cy="100" r="64.5" fill="none" style={{ stroke: genreInk(wheel.empty_color) }} strokeWidth="27" />
          ) : arcs.map(({ segment, path }) => (
            <path key={segment.genre} d={path} style={{ fill: genreInk(segment.color) }}
              className={segment === selected ? styles.selectedArc : styles.arc}
              onPointerEnter={() => setSelectedGenre(segment.genre)}
              onClick={() => setSelectedGenre(segment.genre)}>
              <title>{segment.genre} · {segment.percentage}%</title>
            </path>
          ))}
        </svg>
        <div className={styles.avatar}><Avatar key={user.profile_picture || user.id_user} user={user} size={56} /></div>
      </div>
      <figcaption className={styles.legend}>
        <h2>Genre wheel</h2>
        {empty ? (
          <p className={styles.description}>The wheel fills in when a book with a genre is marked as finished.</p>
        ) : (
          <>
            <p className={styles.description}>Top genres from {plural(wheel.total_books, 'finished book')}, weighted by ratings and favorites.</p>
            <ul className={styles.list} aria-label="Select a genre">
              {segments.map((segment) => (
                <li key={segment.genre}>
                  <button type="button" className={styles.choice} aria-pressed={segment === selected}
                    onClick={() => setSelectedGenre(segment.genre)}>
                    <span className={styles.swatch} style={{ backgroundColor: genreInk(segment.color) }} />
                    <span className={styles.genre}>{segment.genre}</span>
                    <span className="tabular">{segment.percentage}%</span>
                  </button>
                </li>
              ))}
            </ul>
            <div className={styles.detail} role="status" aria-live="polite" aria-atomic="true">
              <strong>{selected.genre}</strong> · {plural(selected.book_count, 'book')} · {selected.average_rating == null
                ? 'No ratings yet' : `${formatRating(selected.average_rating)}/5 average rating`}
            </div>
          </>
        )}
      </figcaption>
    </figure>
  );
}

/** A public reader's wheel is available independently of follower-only statistics. */
export function GenreWheel({ user, state }) {
  const { data, error, loading, reload } = state;
  if (error?.status === 403) return <EmptyState icon="lock" title="This genre wheel is private" />;
  if (error) return <ErrorState title="Genre wheel didn’t load" error={error} onRetry={reload} />;
  if (loading || !data) return <div aria-label="Loading genre wheel" aria-busy="true"><Skeleton height={224} /></div>;
  return <WheelChart key={user.id_user} user={user} wheel={data} />;
}
