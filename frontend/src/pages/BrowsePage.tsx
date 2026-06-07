import { useDeferredValue, useMemo } from 'react';

import { ErrorState } from '@/components/common/ErrorState';
import { Skeleton } from '@/components/common/Skeleton';
import { FilterSidebar } from '@/components/filters/FilterSidebar';
import { KeywordSearch } from '@/components/filters/KeywordSearch';
import { PaperFeed } from '@/components/papers/PaperFeed';
import { useCategories, useTopics } from '@/hooks/useTopics';
import { usePapers } from '@/hooks/usePapers';
import { useFilterParams } from '@/hooks/useFilterParams';
import { applyFilters } from '@/lib/filtering';
import { pluralize } from '@/lib/format';
import styles from './BrowsePage.module.css';

export default function BrowsePage() {
  const controls = useFilterParams();
  const { filters, setKeyword } = controls;

  // Topics/categories/date filter server-side (via the client seam); keyword is applied
  // client-side with a deferred value so typing stays responsive.
  const serverFilters = {
    topics: filters.topics,
    categories: filters.categories,
    from: filters.from,
    to: filters.to,
  };
  const { data, error, isLoading, mutate } = usePapers(serverFilters);
  const { data: topics = [] } = useTopics();
  const { data: categories = [] } = useCategories();

  const deferredKeyword = useDeferredValue(filters.q ?? '');
  const papers = useMemo(
    () => applyFilters(data ?? [], { q: deferredKeyword }),
    [data, deferredKeyword],
  );
  const isStale = deferredKeyword !== (filters.q ?? '');

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <h1 className={styles.title}>Browse</h1>
        <div className={styles.search}>
          <KeywordSearch value={filters.q ?? ''} onChange={setKeyword} />
        </div>
        <p className={styles.resultCount}>
          {isLoading ? 'Loading…' : pluralize(papers.length, 'paper')}
        </p>
      </header>

      <div className={styles.layout}>
        <FilterSidebar controls={controls} topics={topics} categories={categories} />

        <div className={isStale ? styles.stale : undefined}>
          {isLoading ? (
            <Skeleton rows={6} />
          ) : error ? (
            <ErrorState message="Could not load papers." onRetry={() => mutate()} />
          ) : (
            <PaperFeed
              papers={papers}
              emptyTitle="No matching papers"
              emptyHint="Try removing a filter or broadening your search."
            />
          )}
        </div>
      </div>
    </div>
  );
}
