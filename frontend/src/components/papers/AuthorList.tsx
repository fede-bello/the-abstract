import type { Author } from '@/data/types';
import { formatAuthors, leadAffiliation } from '@/lib/format';
import styles from './AuthorList.module.css';

interface AuthorListProps {
  authors: Author[];
  max?: number;
}

/** Compact author line: truncated names + the lead affiliation as a signal. */
export function AuthorList({ authors, max = 4 }: AuthorListProps) {
  if (authors.length === 0) return null;
  const affiliation = leadAffiliation(authors);
  return (
    <p className={styles.line}>
      <span className={styles.names}>{formatAuthors(authors, max)}</span>
      {affiliation && (
        <>
          <span className={styles.sep} aria-hidden="true">
            ·
          </span>
          <span className={styles.affiliation}>{affiliation}</span>
        </>
      )}
    </p>
  );
}
