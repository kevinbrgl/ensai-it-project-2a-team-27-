import { Link } from 'react-router-dom';
import { firstAuthor, yearOf } from '../../utils/format';
import { BookCover } from './BookCover';
import styles from './BookRow.module.css';

/** A book in a management list: small cover, details, and actions on the right. */
export function BookRow({ book, actions, children }) {
  const year = yearOf(book.publish_date);
  return (
    <li className={styles.row}>
      <Link to={`/books/${book.id_book}`} className={styles.coverLink} tabIndex={-1} aria-hidden="true">
        <BookCover book={book} size="sm" decorative />
      </Link>
      <div className={styles.details}>
        <Link to={`/books/${book.id_book}`} className={styles.title}>
          {book.title}
        </Link>
        <p className={styles.meta}>
          {firstAuthor(book.author)}
          {year && <span className="tabular"> · {year}</span>}
          {book.category && <span> · {book.category}</span>}
        </p>
        {children}
      </div>
      {actions && <div className={styles.actions}>{actions}</div>}
    </li>
  );
}
