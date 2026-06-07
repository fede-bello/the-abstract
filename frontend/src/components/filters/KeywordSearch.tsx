import styles from './KeywordSearch.module.css';

interface KeywordSearchProps {
  value: string;
  onChange: (value: string) => void;
}

export function KeywordSearch({ value, onChange }: KeywordSearchProps) {
  return (
    <div className={styles.wrap}>
      <span className={styles.icon} aria-hidden="true">
        /
      </span>
      <input
        type="search"
        className={styles.input}
        placeholder="Search titles, abstracts, authors"
        aria-label="Search papers"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
