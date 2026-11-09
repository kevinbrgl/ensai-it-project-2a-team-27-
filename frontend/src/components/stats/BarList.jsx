import styles from './BarList.module.css';

/** Horizontal bars for a ranked list of { label, value }. */
export function BarList({ items, max }) {
  const top = max ?? Math.max(1, ...items.map((item) => item.value));
  return (
    <ul className={styles.list}>
      {items.map((item) => (
        <li key={item.label} className={styles.row}>
          <span className={styles.label} title={item.label}>
            {item.label}
          </span>
          <span className={styles.track}>
            <span className={styles.bar} style={{ width: `${(item.value / top) * 100}%` }} />
          </span>
          <span className={`${styles.value} tabular`}>{item.value}</span>
        </li>
      ))}
    </ul>
  );
}
