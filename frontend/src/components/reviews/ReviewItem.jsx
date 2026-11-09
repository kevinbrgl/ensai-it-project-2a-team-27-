import { Link } from 'react-router-dom';
import { getKnownUser } from '../../api/users';
import { formatDate } from '../../utils/format';
import { Avatar } from '../ui/Avatar';
import { Stars } from '../ui/StarRating';
import styles from './Reviews.module.css';

/**
 * One review. `heading` replaces the author line (used on profiles, where the
 * book title matters more than the author).
 */
export function ReviewItem({ review, isMine, heading, actions }) {
  const author = getKnownUser(review.id_user);
  const name = isMine ? 'You' : author?.username || `Reader #${review.id_user}`;

  return (
    <article className={styles.item}>
      {heading || (
        <header className={styles.itemHeader}>
          <Link to={`/users/${review.id_user}`} className={styles.author}>
            <Avatar user={author || { id_user: review.id_user, username: name }} size={32} />
            <span className={styles.authorName}>{name}</span>
          </Link>
          {actions}
        </header>
      )}
      <div className={styles.ratingLine}>
        <Stars value={review.rating} />
        <time className={styles.date} dateTime={review.created_at}>
          {formatDate(review.created_at)}
        </time>
        {heading && actions}
      </div>
      {review.comment && <p className={styles.comment}>{review.comment}</p>}
    </article>
  );
}
