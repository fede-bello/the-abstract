import useSWR from 'swr';

import { getClient } from '@/data/client';
import type { Paper, PaperFilters } from '@/data/types';

/** The most recent weekly issue (papers + week summary). */
export function useLatestWeek() {
  return useSWR('latest-week', () => getClient().getLatestWeek());
}

/** Papers matching `filters`. SWR hashes the array key by value, so identical filters dedupe. */
export function usePapers(filters: PaperFilters) {
  return useSWR(['papers', filters], () => getClient().listPapers(filters));
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
