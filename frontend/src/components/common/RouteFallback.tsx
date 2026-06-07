import styles from './RouteFallback.module.css';

/** Full-bleed loading state shown while a lazy route chunk resolves. */
export function RouteFallback() {
  return (
    <div className={styles.wrap} role="status" aria-live="polite">
      <span className={styles.bar} />
      <span className="label">Loading</span>
    </div>
  );
}
