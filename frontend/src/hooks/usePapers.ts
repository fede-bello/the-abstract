import useSWR from 'swr';
import useSWRInfinite from 'swr/infinite';

import { getClient } from '@/data/client';
import type { Paper, PaperFilters } from '@/data/types';

/** Papers fetched per infinite-scroll page. A full page implies more may follow. */
export const PAPERS_PAGE_SIZE = 24;

/** The most recent weekly issue (papers + week summary). */
export function useLatestWeek() {
  return useSWR('latest-week', () => getClient().getLatestWeek());
}

/** Papers matching `filters`. SWR hashes the array key by value, so identical filters dedupe. */
export function usePapers(filters: PaperFilters) {
  return useSWR(['papers', filters], () => getClient().listPapers(filters));
}

/** Papers matching `filters`, fetched a page at a time for infinite scroll. Returns the pages
 *  flattened plus the flags a scroll sentinel needs (`isReachingEnd`, `isLoadingMore`). */
export function usePapersInfinite(filters: PaperFilters) {
  const { data, error, size, setSize, isLoading, isValidating, mutate } = useSWRInfinite(
    (index, previous: Paper[] | null) => {
      if (previous && previous.length < PAPERS_PAGE_SIZE) return null; // last page was short: stop
      return ['papers-page', filters, index] as const;
    },
    ([, pageFilters, index]) =>
      getClient().listPapers(pageFilters, {
        limit: PAPERS_PAGE_SIZE,
        offset: index * PAPERS_PAGE_SIZE,
      }),
    { revalidateFirstPage: false },
  );

  const pages = data ?? [];
  const papers = pages.flat();
  const isLoadingMore = size > pages.length || (isValidating && pages.length > 0);
  const lastPage = pages.at(-1);
  const isReachingEnd = lastPage !== undefined && lastPage.length < PAPERS_PAGE_SIZE;

  return { papers, error, isLoading, isLoadingMore, isReachingEnd, setSize, mutate };
}

/** A single paper by arXiv id; pass undefined to skip the request. */
export function usePaper(arxivId: string | undefined) {
  return useSWR(arxivId ? ['paper', arxivId] : null, ([, id]) => getClient().getPaper(id));
}

/** Papers sharing topics with `paper`, ranked by overlap then recency (excludes itself). */
export function useRelatedPapers(paper: Paper | undefined, limit = 4) {
  return useSWR(paper ? ['related', paper.arxiv_id] : null, async () => {
    if (!paper) return [];
    const candidates = await getClient().listPapers({ topics: paper.topics });
    return candidates
      .filter((p) => p.arxiv_id !== paper.arxiv_id)
      .map((p) => ({ p, shared: p.topics.filter((t) => paper.topics.includes(t)).length }))
      .sort((a, b) => b.shared - a.shared || b.p.published.localeCompare(a.p.published))
      .slice(0, limit)
      .map((r) => r.p);
  });
}
