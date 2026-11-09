import styles from './SegmentedControl.module.css';

/** A row of mutually exclusive options (tabs, sort orders…). */
export function SegmentedControl({ options, value, onChange, label, size = 'md' }) {
  return (
    <div className={`${styles.group} ${styles[size]}`} role="radiogroup" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={value === option.value}
          className={`${styles.option} ${value === option.value ? styles.active : ''}`}
          onClick={() => onChange(option.value)}
        >
          {option.label}
          {option.count !== undefined && <span className={`${styles.count} tabular`}>{option.count}</span>}
        </button>
      ))}
    </div>
  );
}
