// REST implementation of ApiClient — the live data source. Each method maps to one FastAPI
// endpoint (see backend/src/arxiv_digest/api/). Configure the base URL via VITE_API_BASE_URL.

import type { ApiClient } from '@/data/client';
import type {
  AskResponse,
  AskScope,
  Paper,
  PaperFilters,
  TopicCount,
  WeekIssueData,
  WeekSummary,
} from '@/data/types';

function buildQuery(filters?: PaperFilters): string {
  if (!filters) return '';
  const params = new URLSearchParams();
  filters.topics?.forEach((t) => params.append('topic', t));
  filters.categories?.forEach((c) => params.append('category', c));
  if (filters.from) params.set('from', filters.from);
  if (filters.to) params.set('to', filters.to);
  if (filters.q) params.set('q', filters.q);
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

export class RestApiClient implements ApiClient {
  constructor(private readonly baseUrl: string) {}

  private async get<T>(path: string): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`);
    if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
    return res.json() as Promise<T>;
  }

  listPapers(filters?: PaperFilters): Promise<Paper[]> {
    return this.get<Paper[]>(`/papers${buildQuery(filters)}`);
  }

  getPaper(arxivId: string): Promise<Paper | null> {
    return this.get<Paper | null>(`/papers/${encodeURIComponent(arxivId)}`);
  }

  getLatestWeek(): Promise<WeekIssueData | null> {
    return this.get<WeekIssueData | null>('/weeks/latest');
  }

  listWeeks(): Promise<WeekSummary[]> {
    return this.get<WeekSummary[]>('/weeks');
  }

  getWeek(weekKey: string): Promise<WeekIssueData | null> {
    return this.get<WeekIssueData | null>(`/weeks/${encodeURIComponent(weekKey)}`);
  }

  listTopicsWithCounts(): Promise<TopicCount[]> {
    return this.get<TopicCount[]>('/topics');
  }

  listCategories(): Promise<string[]> {
    return this.get<string[]>('/categories');
  }

  async askDummy(question: string, scope: AskScope): Promise<AskResponse> {
    const res = await fetch(`${this.baseUrl}/ask`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ question, scope }),
    });
    if (!res.ok) throw new Error(`POST /ask failed: ${res.status}`);
    return res.json() as Promise<AskResponse>;
  }
}
