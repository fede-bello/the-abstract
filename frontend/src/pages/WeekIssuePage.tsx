import { Link, useParams } from 'react-router-dom';

import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { Skeleton } from '@/components/common/Skeleton';
import { WeekIssue } from '@/components/digest/WeekIssue';
import { useWeek } from '@/hooks/useWeeks';
import { ROUTES } from '@/lib/constants';
import styles from './WeekIssuePage.module.css';

export default function WeekIssuePage() {
  const { weekKey } = useParams<{ weekKey: string }>();
  const { data, error, isLoading, mutate } = useWeek(weekKey);

  if (isLoading) return <Skeleton rows={6} />;
  if (error) return <ErrorState message="Could not load this issue." onRetry={() => mutate()} />;
  if (!data) {
    return (
      <EmptyState
        title="Issue not found"
        hint={`No archived issue for ${weekKey}.`}
        action={
          <Link to={ROUTES.archive} className={styles.back}>
            ← Back to archive
          </Link>
        }
      />
    );
  }

  return (
    <div className={styles.page}>
      <Link to={ROUTES.archive} className={styles.back} viewTransition>
        ← Archive
      </Link>
      <WeekIssue issue={data} kicker="Archive issue" />
    </div>
  );
}
