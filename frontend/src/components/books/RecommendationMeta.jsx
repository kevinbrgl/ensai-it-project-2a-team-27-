import { formatRating } from '../../utils/format';
import { Icon } from '../ui/Icon';
import styles from './RecommendationMeta.module.css';

/** Score and reason under a recommended book, as returned by /recommendations. */
export function RecommendationMeta({ rec }) {
  return (
    <span className={styles.meta}>
      {rec.score != null && (
        <span className={`${styles.score} tabular`}>
          <Icon name="star" size={13} filled /> {formatRating(rec.score)}
        </span>
      )}
      <span className={styles.reason}>{rec.reason}</span>
    </span>
  );
}
