import styles from './ProgressSummary.module.css';

const percent = (done, total) => (total ? Math.round((100 * done) / total) : 0);

/**
 * A large summary band: headline figures, one overall progress rail and a
 * done / total breakdown (by tier or category).
 *
 * figures: [{ key, value, total?, unit?, caption }]
 * breakdown: [{ key, label, done, total, tone? }]; `tone` picks a medal colour.
 */
export function ProgressSummary({ label, figures, share, breakdown }) {
  return (
    <div className={styles.summary} role="group" aria-label={label}>
      <div className={styles.overall}>
        <div className={styles.figures}>
          {figures.map((figure) => (
            <p key={figure.key} className={styles.figure}>
              <span className={`${styles.value} tabular`}>
                {figure.value.toLocaleString()}
                {figure.total !== undefined && (
                  <span className={styles.total}> / {figure.total.toLocaleString()}</span>
                )}
                {/* "430 / 1,420 XP" but "15%": a unit after a total needs a space. */}
                {figure.unit && (
                  <span className={styles.unit}>{figure.total !== undefined ? ` ${figure.unit}` : figure.unit}</span>
                )}
              </span>
              <span className={styles.caption}>{figure.caption}</span>
            </p>
          ))}
        </div>
        <div
          className={styles.rail}
          role="progressbar"
          aria-label={`${label}: ${share}%`}
          aria-valuenow={share}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <span style={{ width: `${share}%` }} />
        </div>
      </div>
      <dl className={styles.breakdown}>
        {breakdown.map((item) => (
          <div key={item.key} className={styles.cell} data-tone={item.tone}>
            <dt>{item.label}</dt>
            <dd>
              <span className="tabular">
                <span className={styles.done}>{item.done}</span>
                <span className={styles.of}> / {item.total}</span>
              </span>
              <span className={styles.bar} aria-hidden="true">
                <span style={{ width: `${percent(item.done, item.total)}%` }} />
              </span>
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
