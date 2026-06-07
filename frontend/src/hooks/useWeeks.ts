import useSWR from 'swr';

import { getClient } from '@/data/client';

/** All weekly issues (summaries only), newest first. */
export function useWeeks() {
  return useSWR('weeks', () => getClient().listWeeks());
}

/** A single weekly issue by ISO week key (e.g. "2026-W23"). */
export function useWeek(weekKey: string | undefined) {
  return useSWR(weekKey ? ['week', weekKey] : null, ([, key]) => getClient().getWeek(key));
}
