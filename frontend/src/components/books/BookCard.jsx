import { Link } from 'react-router-dom';
import { useLibrary } from '../../context/LibraryContext';
import { STATUS_LABELS, firstAuthor, yearOf } from '../../utils/format';
import { BookCover } from './BookCover';
import styles from './BookCard.module.css';

/** Cover + title + author, linking to the book page. `meta` adds a line below. */
export function BookCard({ book, meta, showStatus = true }) {
  const library = useLibrary();
  const entry = showStatus ? library.get(book.id_book) : null;
  const year = yearOf(book.publish_date);

  return (
    <Link to={`/books/${book.id_book}`} className={styles.card}>
      <div className={styles.coverWrap}>
        <BookCover book={book} decorative />
        {entry && <span className={`${styles.status} ${styles[entry.state]}`}>{STATUS_LABELS[entry.state]}</span>}
      </div>
      <div className={styles.text}>
        <h3 className={styles.title}>{book.title}</h3>
        <p className={styles.author}>
          {firstAuthor(book.author)}
          {year && <span className="tabular"> · {year}</span>}
        </p>
        {meta && <div className={styles.meta}>{meta}</div>}
      </div>
    </Link>
  );
}
