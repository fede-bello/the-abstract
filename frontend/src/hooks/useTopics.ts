import useSWR from 'swr';

import { getClient } from '@/data/client';

/** Topic facets with paper counts, in taxonomy order (empty topics omitted). */
export function useTopics() {
  return useSWR('topics', () => getClient().listTopicsWithCounts());
}

/** arXiv category codes present in the corpus. */
export function useCategories() {
  return useSWR('categories', () => getClient().listCategories());
}
