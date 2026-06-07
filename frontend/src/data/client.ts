// The data-access seam. Components NEVER import a concrete client — they use the hooks in
// src/hooks, which call getClient(). Swapping mock <-> REST is a one-line env change here.

import type {
  AskResponse,
  AskScope,
  Paper,
  PaperFilters,
  TopicCount,
  WeekIssueData,
  WeekSummary,
} from './types';
import { RestApiClient } from './rest/restClient';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';

/** Every method's signature matches a future REST endpoint (see rest/restClient.ts). */
export interface ApiClient {
  listPapers(filters?: PaperFilters): Promise<Paper[]>; // GET /papers
  getPaper(arxivId: string): Promise<Paper | null>; // GET /papers/:id
  getLatestWeek(): Promise<WeekIssueData | null>; // GET /weeks/latest
  listWeeks(): Promise<WeekSummary[]>; // GET /weeks
  getWeek(weekKey: string): Promise<WeekIssueData | null>; // GET /weeks/:key
  listTopicsWithCounts(): Promise<TopicCount[]>; // GET /topics
  listCategories(): Promise<string[]>; // GET /categories
  askDummy(question: string, scope: AskScope): Promise<AskResponse>; // POST /ask (RAG later)
}

let client: ApiClient | null = null;

/** Returns the process-wide client (a RestApiClient), built once on first use. */
export function getClient(): ApiClient {
  if (client) return client;
  client = new RestApiClient(import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL);
  return client;
}
