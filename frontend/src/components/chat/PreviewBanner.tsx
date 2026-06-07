import styles from './PreviewBanner.module.css';

/** Stays until the real RAG backend lands. Removing the dummy = delete this + wire restClient. */
export function PreviewBanner() {
  return (
    <div className={styles.banner} role="note">
      <span className={styles.tag}>Preview</span>
      <p className={styles.text}>
        Question answering over the full paper database (RAG) isn’t live yet. Answers below are
        placeholders — the real retrieval-grounded responses are coming soon.
      </p>
    </div>
  );
}
