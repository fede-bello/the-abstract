import { Link, useParams } from 'react-router-dom';

import { Collapsible } from '@/components/common/Collapsible';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { ExternalLink } from '@/components/common/ExternalLink';
import { Skeleton } from '@/components/common/Skeleton';
import { CategoryBadge } from '@/components/papers/CategoryBadge';
import { RelatedPapers } from '@/components/papers/RelatedPapers';
import { TopicTagList } from '@/components/papers/TopicTagList';
import { usePaper } from '@/hooks/usePapers';
import { ROUTES } from '@/lib/constants';
import { formatDate, toBullets } from '@/lib/format';
import styles from './PaperDetailPage.module.css';

export default function PaperDetailPage() {
  const { arxivId } = useParams<{ arxivId: string }>();
  const { data: paper, error, isLoading, mutate } = usePaper(arxivId);

  if (isLoading) return <Skeleton rows={5} />;
  if (error) return <ErrorState message="Could not load this paper." onRetry={() => mutate()} />;
  if (!paper) {
    return (
      <EmptyState
        title="Paper not found"
        hint={`No paper with id ${arxivId}.`}
        action={
          <Link to={ROUTES.browse} className={styles.backLink}>
            ← Back to browse
          </Link>
        }
      />
    );
  }

  const bullets = paper.summary ? toBullets(paper.summary.short) : [];

  return (
    <article className={styles.page}>
      <Link to={ROUTES.browse} className={styles.back} viewTransition>
        ← All papers
      </Link>

      <header className={styles.header}>
        <TopicTagList topics={paper.topics} linked />
        <h1 className={styles.title}>{paper.title}</h1>

        <ul className={styles.authors}>
          {paper.authors.map((author) => (
            <li key={author.name} className={styles.author}>
              <span className={styles.authorName}>{author.name}</span>
              {author.affiliation && (
                <span className={styles.authorAffil}>{author.affiliation}</span>
              )}
            </li>
          ))}
        </ul>

        <div className={styles.metaBar}>
          <span className="mono">{formatDate(paper.published)}</span>
          <span className={styles.metaSep}>/</span>
          <CategoryBadge code={paper.primary_category} />
          <span className={styles.metaSep}>/</span>
          <span className="mono">{paper.arxiv_id}</span>
        </div>

        <div className={styles.actions}>
          <ExternalLink href={paper.entry_id} className={styles.actionPrimary}>
            arXiv
          </ExternalLink>
          <ExternalLink href={paper.pdf_url} className={styles.action}>
            PDF
          </ExternalLink>
        </div>
      </header>

      {bullets.length > 0 && (
        <section className={styles.section}>
          <h2 className={styles.heading}>Summary</h2>
          <ul className={styles.summaryBullets}>
            {bullets.map((bullet, i) => (
              <li key={i}>{bullet}</li>
            ))}
          </ul>
        </section>
      )}

      {paper.summary?.long && (
        <section className={styles.section}>
          <h2 className={styles.heading}>Details</h2>
          {paper.summary.long.split('\n\n').map((para, i) => (
            <p key={i} className={styles.prose}>
              {para}
            </p>
          ))}
        </section>
      )}

      {paper.summary?.conclusions && (
        <section className={styles.section}>
          <h2 className={styles.heading}>Why it matters</h2>
          <p className={styles.prose}>{paper.summary.conclusions}</p>
        </section>
      )}

      <section className={styles.section}>
        <h2 className={styles.heading}>Abstract</h2>
        <p className={`${styles.prose} ${styles.abstract}`}>{paper.abstract}</p>
      </section>

      {paper.classification_rationale && (
        <Collapsible label="Why we picked this">
          <p>{paper.classification_rationale}</p>
        </Collapsible>
      )}

      <RelatedPapers paper={paper} />
    </article>
  );
}
