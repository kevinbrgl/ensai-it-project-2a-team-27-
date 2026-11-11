import { BarList } from './BarList';
import styles from './StatsPanels.module.css';

/** Renders a UserStats object: books finished, genres and ratings. */
export function StatsPanels({ stats, libraryCount }) {
  const genres = stats.genres.map((g) => ({ label: g.category || 'Uncategorised', value: g.count })).slice(0, 8);
  const ratings = [...stats.ratings].sort((a, b) => b.rating - a.rating).map((r) => ({ label: `${r.rating} ★`, value: r.count }));
  const totalRatings = stats.ratings.reduce((sum, r) => sum + r.count, 0);
  const average = totalRatings ? stats.ratings.reduce((sum, r) => sum + r.rating * r.count, 0) / totalRatings : null;

  return (
    <div className={styles.grid}>
      <div className={`${styles.card} ${styles.figures}`}>
        <Figure value={stats.books_finished} label="Books finished" />
        {libraryCount !== undefined && <Figure value={libraryCount} label="In the library" />}
        <Figure value={totalRatings} label="Books rated" />
        <Figure value={average ? average.toFixed(1) : '–'} label="Average rating given" />
      </div>
      <div className={styles.card}>
        <h3 className={styles.title}>Genres in the library</h3>
        {genres.length ? <BarList items={genres} /> : <p className={styles.muted}>No books in the library yet.</p>}
      </div>
      <div className={styles.card}>
        <h3 className={styles.title}>Ratings given</h3>
        {totalRatings ? <BarList items={ratings} /> : <p className={styles.muted}>No reviews written yet.</p>}
      </div>
    </div>
  );
}

function Figure({ value, label }) {
  return (
    <div className={styles.figure}>
      <span className={`${styles.value} tabular`}>{value}</span>
      <span className={styles.label}>{label}</span>
    </div>
  );
}
