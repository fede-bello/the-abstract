import { useSearchParams } from 'react-router-dom';

import styles from './ScopeChips.module.css';

interface ScopeChipsProps {
  paperId?: string;
  paperTitle?: string;
  topics: string[];
}

/** Shows the current Q&A scope (paper or topics) as removable chips backed by the URL. */
export function ScopeChips({ paperId, paperTitle, topics }: ScopeChipsProps) {
  const [params, setParams] = useSearchParams();

  const removeParam = (key: string, value?: string) => {
    const next = new URLSearchParams(params);
    if (value === undefined) next.delete(key);
    else {
      const remaining = next.getAll(key).filter((v) => v !== value);
      next.delete(key);
      remaining.forEach((v) => next.append(key, v));
    }
    setParams(next, { replace: true });
  };

  const hasScope = Boolean(paperId) || topics.length > 0;

  return (
    <div className={styles.wrap}>
      <span className="label">Scope</span>
      {!hasScope && <span className={styles.all}>Whole archive</span>}

      {paperId && (
        <button type="button" className={styles.chip} onClick={() => removeParam('paper')}>
          <span className={styles.chipLabel}>{paperTitle ?? paperId}</span>
          <span className={styles.x} aria-hidden="true">
            ×
          </span>
          <span className="sr-only">Remove paper scope</span>
        </button>
      )}

      {topics.map((topic) => (
        <button
          key={topic}
          type="button"
          className={styles.chip}
          onClick={() => removeParam('topic', topic)}
        >
          <span className={styles.chipLabel}>{topic}</span>
          <span className={styles.x} aria-hidden="true">
            ×
          </span>
          <span className="sr-only">Remove {topic} scope</span>
        </button>
      ))}
    </div>
  );
}
