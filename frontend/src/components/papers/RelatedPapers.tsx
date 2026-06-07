import { Link } from 'react-router-dom';

import type { Paper } from '@/data/types';
import { useRelatedPapers } from '@/hooks/usePapers';
import { ROUTES } from '@/lib/constants';
import { formatAuthors } from '@/lib/format';
import { TopicTagList } from './TopicTagList';
import styles from './RelatedPapers.module.css';

interface RelatedPapersProps {
  paper: Paper;
}

export function RelatedPapers({ paper }: RelatedPapersProps) {
  const { data: related = [] } = useRelatedPapers(paper);
  if (related.length === 0) return null;

  return (
    <section className={styles.section} aria-label="Related papers">
      <h2 className={styles.heading}>Related</h2>
      <ul className={styles.list}>
        {related.map((rel) => (
          <li key={rel.arxiv_id}>
            <Link to={ROUTES.paper(rel.arxiv_id)} className={styles.item} viewTransition>
              <span className={styles.title}>{rel.title}</span>
              <span className={styles.authors}>{formatAuthors(rel.authors, 2)}</span>
            </Link>
            <TopicTagList topics={rel.topics.slice(0, 3)} />
          </li>
        ))}
      </ul>
    </section>
  );
}
