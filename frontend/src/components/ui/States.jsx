import { Button } from './Button';
import { Icon } from './Icon';
import styles from './States.module.css';

/** Shown when a list is empty. Give it a next step whenever possible. */
export function EmptyState({ icon = 'book', title, children, action }) {
  return (
    <div className={styles.state}>
      <span className={styles.icon}>
        <Icon name={icon} size={22} />
      </span>
      <h3 className={styles.title}>{title}</h3>
      {children && <p className={styles.text}>{children}</p>}
      {action && <div className={styles.action}>{action}</div>}
    </div>
  );
}

/** Shown when a request failed, with a retry button. */
export function ErrorState({ error, onRetry, title = 'This didn’t load' }) {
  return (
    <div className={`${styles.state} ${styles.error}`} role="alert">
      <span className={styles.icon}>
        <Icon name="alert" size={22} />
      </span>
      <h3 className={styles.title}>{title}</h3>
      <p className={styles.text}>{error?.message || 'Something went wrong.'}</p>
      {onRetry && (
        <div className={styles.action}>
          <Button size="sm" icon="refresh" onClick={onRetry}>
            Try again
          </Button>
        </div>
      )}
    </div>
  );
}
