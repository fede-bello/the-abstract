// The data-access seam. Components NEVER import a concrete client — they use the hooks in
// src/hooks, which call getClient(). The app reads Supabase (Postgres) directly via the anon
// key; swapping the data source is a one-line change here.

import type {
  Paper,
  PaperFilters,
  TopicCount,
  WeekIssueData,
  WeekSummary,
} from './types';
import { SupabaseApiClient } from './supabase/supabaseClient';

/** The data-access contract the hooks depend on. Implemented by SupabaseApiClient. */
export interface ApiClient {
  listPapers(filters?: PaperFilters): Promise<Paper[]>;
  getPaper(arxivId: string): Promise<Paper | null>;
  getLatestWeek(): Promise<WeekIssueData | null>;
  listWeeks(): Promise<WeekSummary[]>;
  getWeek(weekKey: string): Promise<WeekIssueData | null>;
  listTopicsWithCounts(): Promise<TopicCount[]>;
  listCategories(): Promise<string[]>;
}

let client: ApiClient | null = null;

/** Returns the process-wide client (a SupabaseApiClient), built once on first use. */
export function getClient(): ApiClient {
  if (client) return client;
  const url = import.meta.env.VITE_SUPABASE_URL;
  const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
  if (!url || !anonKey) {
    throw new Error('VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY must be set (see .env.example).');
  }
  client = new SupabaseApiClient(url, anonKey);
  return client;
}
