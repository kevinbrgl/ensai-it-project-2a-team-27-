import styles from './Spinner.module.css';

export function Spinner({ size = 18 }) {
  return <span className={styles.spinner} style={{ width: size, height: size }} aria-label="Loading" />;
}
