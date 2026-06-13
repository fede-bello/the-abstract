import { Link } from 'react-router-dom';

import { ErrorState } from '@/components/common/ErrorState';
import { Skeleton } from '@/components/common/Skeleton';
import { EmptyState } from '@/components/common/EmptyState';
import { WeekIssue } from '@/components/digest/WeekIssue';
import { SubscribeForm } from '@/components/layout/SubscribeForm';
import { useLatestWeek } from '@/hooks/usePapers';
import { ROUTES } from '@/lib/constants';
import styles from './HomePage.module.css';

export default function HomePage() {
  const { data, error, isLoading, mutate } = useLatestWeek();

  if (isLoading) return <Skeleton rows={8} />;
  if (error) return <ErrorState message="Could not load this week's issue." onRetry={() => mutate()} />;
  if (!data) return <EmptyState title="No issue yet" hint="The first weekly digest will appear here." />;

  return (
    <div className={styles.page}>
      <section className={styles.subscribe}>
        <div className={styles.subscribeCopy}>
          <p className={styles.subscribeKicker}>Weekly newsletter</p>
          <h2 className={styles.subscribeHeading}>The week in ML, in your inbox.</h2>
          <p className={styles.subscribeText}>
            One email every Monday — the arXiv papers worth your attention, summarized. Free, no
            spam, unsubscribe anytime.
          </p>
        </div>
        <SubscribeForm />
      </section>

      <WeekIssue issue={data} kicker="This week" />

      <nav className={styles.cta}>
        <Link to={ROUTES.browse} className={styles.ctaLink} viewTransition>
          Browse all papers
          <span aria-hidden="true"> →</span>
        </Link>
        <Link to={ROUTES.archive} className={styles.ctaLink} viewTransition>
          Past issues
          <span aria-hidden="true"> →</span>
        </Link>
      </nav>
    </div>
  );
}
