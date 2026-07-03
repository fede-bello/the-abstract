import { useCallback, useDeferredValue, useEffect, useMemo, useRef } from 'react';

import { ErrorState } from '@/components/common/ErrorState';
import { Skeleton } from '@/components/common/Skeleton';
import { FilterSidebar } from '@/components/filters/FilterSidebar';
import { KeywordSearch } from '@/components/filters/KeywordSearch';
import { PaperFeed } from '@/components/papers/PaperFeed';
import { useCategories, useTopics } from '@/hooks/useTopics';
import { usePapersInfinite } from '@/hooks/usePapers';
import { useFilterParams } from '@/hooks/useFilterParams';
import { pluralize } from '@/lib/format';
import styles from './BrowsePage.module.css';

export default function BrowsePage() {
  const controls = useFilterParams();
  const { filters, setKeyword } = controls;

  // Keyword is deferred so typing stays responsive; all filters (keyword included) are applied
  // server-side now, so pagination and search compose instead of only searching loaded pages.
  const deferredKeyword = useDeferredValue(filters.q ?? '');
  const serverFilters = useMemo(
    () => ({
      topics: filters.topics,
      categories: filters.categories,
      from: filters.from,
      to: filters.to,
      q: deferredKeyword || undefined,
    }),
    [filters.topics, filters.categories, filters.from, filters.to, deferredKeyword],
  );

  const { papers, error, isLoading, isLoadingMore, isReachingEnd, setSize, mutate } =
    usePapersInfinite(serverFilters);
  const { data: topics = [] } = useTopics();
  const { data: categories = [] } = useCategories();

  // A stable "advance one page" that reads the latest flags through a ref, so the scroll observer
  // can be created once instead of being torn down and rebuilt every time a page loads.
  const latest = useRef({ isLoadingMore, isReachingEnd });
  latest.current = { isLoadingMore, isReachingEnd };
  const loadMore = useCallback(() => {
    if (latest.current.isLoadingMore || latest.current.isReachingEnd) return;
    void setSize((size) => size + 1);
  }, [setSize]);

  // New filters mean a new result set: collapse back to the first page (only when it truly changes).
  const filterKey = JSON.stringify(serverFilters);
  const prevFilterKey = useRef(filterKey);
  useEffect(() => {
    if (prevFilterKey.current === filterKey) return;
    prevFilterKey.current = filterKey;
    void setSize(1);
  }, [filterKey, setSize]);

  // Auto-load the next page when the sentinel nears the viewport. A callback ref (not an effect)
  // attaches the observer exactly when the sentinel mounts, which matters because the sentinel only
  // renders after the first page loads — an effect would run too early, while the ref is still null.
  const observerRef = useRef<IntersectionObserver | null>(null);
  const sentinelRef = useCallback(
    (node: HTMLDivElement | null) => {
      observerRef.current?.disconnect();
      if (!node) return;
      observerRef.current = new IntersectionObserver(
        (entries) => entries[0]?.isIntersecting && loadMore(),
        { rootMargin: '600px' },
      );
      observerRef.current.observe(node);
    },
    [loadMore],
  );

  const isStale = deferredKeyword !== (filters.q ?? '');
  const count = isReachingEnd ? pluralize(papers.length, 'paper') : `${papers.length}+ papers`;

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <h1 className={styles.title}>Browse</h1>
        <div className={styles.search}>
          <KeywordSearch value={filters.q ?? ''} onChange={setKeyword} />
        </div>
        <p className={styles.resultCount}>{isLoading ? 'Loading…' : count}</p>
      </header>

      <div className={styles.layout}>
        <FilterSidebar controls={controls} topics={topics} categories={categories} />

        <div className={isStale ? styles.stale : undefined}>
          {isLoading ? (
            <Skeleton rows={6} />
          ) : error ? (
            <ErrorState message="Could not load papers." onRetry={() => void mutate()} />
          ) : (
            <>
              <PaperFeed
                papers={papers}
                emptyTitle="No matching papers"
                emptyHint="Try removing a filter or broadening your search."
              />
              {!isReachingEnd && (
                <div ref={sentinelRef} className={styles.sentinel}>
                  {isLoadingMore ? (
                    <Skeleton rows={3} />
                  ) : (
                    <button type="button" className={styles.loadMore} onClick={loadMore}>
                      Load more
                    </button>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
