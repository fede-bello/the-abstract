import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';

import type { PaperFilters } from '@/data/types';

export interface FilterControls {
  filters: PaperFilters;
  /** Count of active filter constraints — for badges / "clear all" visibility. */
  activeCount: number;
  toggleTopic: (topic: string) => void;
  toggleCategory: (code: string) => void;
  setDateRange: (from: string | undefined, to: string | undefined) => void;
  setKeyword: (q: string) => void;
  clearAll: () => void;
}

function toSearchParams(filters: PaperFilters): URLSearchParams {
  const sp = new URLSearchParams();
  filters.topics?.forEach((t) => sp.append('topic', t));
  filters.categories?.forEach((c) => sp.append('category', c));
  if (filters.from) sp.set('from', filters.from);
  if (filters.to) sp.set('to', filters.to);
  if (filters.q) sp.set('q', filters.q);
  return sp;
}

/** Browse filters live entirely in the URL: shareable, back-button-correct, single source. */
export function useFilterParams(): FilterControls {
  const [params, setParams] = useSearchParams();

  const filters = useMemo<PaperFilters>(
    () => ({
      topics: params.getAll('topic'),
      categories: params.getAll('category'),
      from: params.get('from') ?? undefined,
      to: params.get('to') ?? undefined,
      q: params.get('q') ?? undefined,
    }),
    [params],
  );

  const update = useCallback(
    (next: PaperFilters) => setParams(toSearchParams(next), { replace: true }),
    [setParams],
  );

  const patch = useCallback(
    (delta: Partial<PaperFilters>) => update({ ...filters, ...delta }),
    [filters, update],
  );

  const toggleTopic = useCallback(
    (topic: string) => {
      const current = filters.topics ?? [];
      patch({
        topics: current.includes(topic)
          ? current.filter((t) => t !== topic)
          : [...current, topic],
      });
    },
    [filters.topics, patch],
  );

  const toggleCategory = useCallback(
    (code: string) => {
      const current = filters.categories ?? [];
      patch({
        categories: current.includes(code)
          ? current.filter((c) => c !== code)
          : [...current, code],
      });
    },
    [filters.categories, patch],
  );

  const setDateRange = useCallback(
    (from: string | undefined, to: string | undefined) => patch({ from, to }),
    [patch],
  );

  const setKeyword = useCallback((q: string) => patch({ q: q || undefined }), [patch]);

  const clearAll = useCallback(() => update({}), [update]);

  const activeCount =
    (filters.topics?.length ?? 0) +
    (filters.categories?.length ?? 0) +
    (filters.from ? 1 : 0) +
    (filters.to ? 1 : 0) +
    (filters.q ? 1 : 0);

  return {
    filters,
    activeCount,
    toggleTopic,
    toggleCategory,
    setDateRange,
    setKeyword,
    clearAll,
  };
}
