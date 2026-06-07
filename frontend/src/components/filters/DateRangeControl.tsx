import styles from './DateRangeControl.module.css';

interface DateRangeControlProps {
  from: string | undefined;
  to: string | undefined;
  onChange: (from: string | undefined, to: string | undefined) => void;
}

export function DateRangeControl({ from, to, onChange }: DateRangeControlProps) {
  return (
    <div className={styles.wrap}>
      <label className={styles.field}>
        <span className="label">From</span>
        <input
          type="date"
          className={styles.input}
          value={from ?? ''}
          onChange={(e) => onChange(e.target.value || undefined, to)}
        />
      </label>
      <label className={styles.field}>
        <span className="label">To</span>
        <input
          type="date"
          className={styles.input}
          value={to ?? ''}
          onChange={(e) => onChange(from, e.target.value || undefined)}
        />
      </label>
    </div>
  );
}
