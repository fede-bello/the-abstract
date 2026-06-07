import { ArchiveIndex } from '@/components/digest/ArchiveIndex';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { Skeleton } from '@/components/common/Skeleton';
import { useWeeks } from '@/hooks/useWeeks';
import { pluralize } from '@/lib/format';
import styles from './ArchivePage.module.css';

export default function ArchivePage() {
  const { data: weeks, error, isLoading, mutate } = useWeeks();

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <span className="label">Archive</span>
        <h1 className={styles.title}>Every issue</h1>
        {weeks && weeks.length > 0 && (
          <p className={styles.sub}>{pluralize(weeks.length, 'weekly issue')}, newest first.</p>
        )}
      </header>

      {isLoading ? (
        <Skeleton rows={5} />
      ) : error ? (
        <ErrorState message="Could not load the archive." onRetry={() => mutate()} />
      ) : !weeks || weeks.length === 0 ? (
        <EmptyState title="No issues yet" hint="Past weekly digests will be listed here." />
      ) : (
        <ArchiveIndex weeks={weeks} />
      )}
    </div>
  );
}
