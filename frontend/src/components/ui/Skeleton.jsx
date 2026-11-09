import styles from './Skeleton.module.css';

export function Skeleton({ width = '100%', height = 14, radius, className = '', style }) {
  return (
    <span
      className={`${styles.skeleton} ${className}`}
      style={{ width, height, borderRadius: radius, ...style }}
      aria-hidden="true"
    />
  );
}
