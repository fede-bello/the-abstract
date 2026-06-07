import { Link } from 'react-router-dom';

import type { Paper } from '@/data/types';
import { ROUTES } from '@/lib/constants';
import { formatDateNumeric, indexLabel, toBullets } from '@/lib/format';
import { AuthorList } from './AuthorList';
import { CategoryBadge } from './CategoryBadge';
import { TopicTagList } from './TopicTagList';
import styles from './PaperIndexRow.module.css';

interface PaperIndexRowProps {
  paper: Paper;
  /** 1-based position in the list, shown as the row number. */
  position: number;
}

const MAX_BULLETS = 2;

export function PaperIndexRow({ paper, position }: PaperIndexRowProps) {
  const bullets = paper.summary ? toBullets(paper.summary.short).slice(0, MAX_BULLETS) : [];
  // Cascade the load-in; cap so deep rows don't lag when scrolled into view.
  const revealDelay = `${Math.min(position - 1, 8) * 35}ms`;

  return (
    <article className={styles.row} style={{ animationDelay: revealDelay }}>
      <div className={styles.index}>
        <span className="mono">{indexLabel(position)}</span>
      </div>

      <div className={styles.main}>
        <h3 className={styles.title}>
          <Link to={ROUTES.paper(paper.arxiv_id)} className={styles.titleLink} viewTransition>
            {paper.title}
          </Link>
        </h3>

        <AuthorList authors={paper.authors} />

        {bullets.length > 0 && (
          <ul className={styles.bullets}>
            {bullets.map((bullet, i) => (
              <li key={i}>{bullet}</li>
            ))}
          </ul>
        )}

        <TopicTagList topics={paper.topics} linked />
      </div>

      <div className={styles.meta}>
        <span className="mono">{formatDateNumeric(paper.published)}</span>
        <CategoryBadge code={paper.primary_category} />
      </div>
    </article>
  );
}
