import { Link, useLocation } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Icon } from '../components/ui/Icon';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import styles from './NotFoundPage.module.css';

export function NotFoundPage() {
  useDocumentTitle('Page not found');
  const { pathname } = useLocation();
  return (
    <section className={styles.page}>
      <div className={styles.card} aria-hidden="true">
        <span className={styles.callNumber}>404</span>
        <span className={styles.cardTitle}>{pathname}</span>
        <span className={styles.stamp}>Not on file</span>
      </div>
      <div className={styles.text}>
        <p className={styles.kicker}>Error 404</p>
        <h1>Out of <em>print.</em></h1>
        <p className={styles.lede}>There’s no page at this address. The link may be broken, or the page may have moved.</p>
        <div className={styles.actions}>
          <Button variant="primary" to="/">Back to the reading room</Button>
          <Link to="/discover" className={styles.link}>Search for a book <Icon name="arrowRight" size={15} /></Link>
        </div>
      </div>
    </section>
  );
}
