import { formatDate, pluralize } from '@/lib/format';
import styles from './Masthead.module.css';

interface MastheadProps {
  kicker: string;
  title: string;
  count: number;
  dateRange?: { start: string; end: string };
}

/** The issue header: a kicker, an oversized title, and a count/date metadata strip. */
export function Masthead({ kicker, title, count, dateRange }: MastheadProps) {
  return (
    <header className={styles.masthead}>
      <div className={styles.topline}>
        <span className="label">{kicker}</span>
        {dateRange && (
          <span className="mono">
            {formatDate(dateRange.start)} — {formatDate(dateRange.end)}
          </span>
        )}
      </div>

      <h1 className={styles.title}>{title}</h1>

      <p className={styles.count}>
        <span className={styles.countNum}>{count}</span>
        <span className={styles.countWord}>{pluralize(count, 'paper').replace(/^\d+\s/, '')}</span>
        <span className={styles.countTail}>worth your attention</span>
      </p>
    </header>
  );
}
