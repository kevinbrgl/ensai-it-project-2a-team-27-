import { Button } from './Button';
import styles from './Pagination.module.css';

export function Pagination({ page, pageCount, total, pageSize, onChange, noun = 'books' }) {
  if (pageCount <= 1) return null;
  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  const go = (next) => {
    onChange(next);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <nav className={styles.pagination} aria-label="Pagination">
      <span className={`${styles.range} tabular`}>
        {from}–{to} of {total} {noun}
      </span>
      <div className={styles.controls}>
        <Button size="sm" icon="chevronLeft" onClick={() => go(page - 1)} disabled={page === 1}>
          Previous
        </Button>
        <span className={`${styles.page} tabular`}>
          {page} / {pageCount}
        </span>
        <Button size="sm" iconRight="chevronRight" onClick={() => go(page + 1)} disabled={page === pageCount}>
          Next
        </Button>
      </div>
    </nav>
  );
}
