import styles from './ChipGroup.module.css';

/** Single-choice filter chips. Clicking the active chip clears the filter. */
export function ChipGroup({ options, value, onChange, label, allLabel = 'All' }) {
  return (
    <div className={styles.chips} role="group" aria-label={label}>
      <button
        type="button"
        className={`${styles.chip} ${!value ? styles.active : ''}`}
        aria-pressed={!value}
        onClick={() => onChange('')}
      >
        {allLabel}
      </button>
      {options.map((option) => {
        const active = value === option.name;
        return (
          <button
            key={option.name}
            type="button"
            className={`${styles.chip} ${active ? styles.active : ''}`}
            aria-pressed={active}
            onClick={() => onChange(active ? '' : option.name)}
          >
            {option.name}
            {option.count !== undefined && <span className={`${styles.count} tabular`}>{option.count}</span>}
          </button>
        );
      })}
    </div>
  );
}
