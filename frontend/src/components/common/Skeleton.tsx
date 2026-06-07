import styles from './Skeleton.module.css';

interface SkeletonProps {
  /** Number of placeholder rows to render. */
  rows?: number;
}

/** Loading placeholder shaped like the index feed. */
export function Skeleton({ rows = 6 }: SkeletonProps) {
  return (
    <div className={styles.list} aria-hidden="true">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className={styles.row}>
          <span className={styles.num} />
          <span className={styles.body}>
            <span className={styles.line} />
            <span className={`${styles.line} ${styles.short}`} />
          </span>
        </div>
      ))}
    </div>
  );
}
