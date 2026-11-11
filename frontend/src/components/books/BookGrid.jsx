import { Skeleton } from '../ui/Skeleton';
import { BookCard } from './BookCard';
import styles from './BookGrid.module.css';

export function BookGrid({ books, renderMeta, variant = 'default' }) {
  return (
    <div className={`${styles.grid} ${styles[variant]}`}>
      {books.map((book) => (
        <BookCard key={book.id_book} book={book} meta={renderMeta?.(book)} />
      ))}
    </div>
  );
}

export function BookGridSkeleton({ count = 12, variant = 'default' }) {
  return (
    <div className={`${styles.grid} ${styles[variant]}`} aria-busy="true" aria-label="Loading books">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className={styles.skeletonCard}>
          <Skeleton style={{ aspectRatio: '2 / 3', height: 'auto' }} radius="var(--radius-cover)" />
          <Skeleton width="85%" height={16} />
          <Skeleton width="55%" height={12} />
        </div>
      ))}
    </div>
  );
}
