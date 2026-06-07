// Supabase implementation of ApiClient — the live data source. The SPA reads Postgres directly
// through Supabase's auto-generated REST API (PostgREST) using the public anon key; row-level
// security on `papers` (see supabase/migrations/0001_init.sql) makes reads safe and read-only.
// Derived data (weekly issues, topic/category facets) comes from read-only views in 0004.
//
// Weeks are never stored: we derive a week's bounds from its key (src/data/week.ts) and fetch
// the papers in that date range, mirroring how the pipeline groups by ISO week.

import { createClient, type SupabaseClient } from '@supabase/supabase-js';

import type { ApiClient } from '@/data/client';
import type {
  AskResponse,
  Paper,
  PaperFilters,
  TopicCount,
  WeekIssueData,
  WeekSummary,
} from '@/data/types';
import { TOPICS } from '@/data/taxonomy';
import { weekKeyBounds, weekLabel } from '@/data/week';

// Columns served to list/week views — everything on Paper except the large `full_text`, which
// is fetched only for a single paper.
const LIST_COLUMNS =
  'arxiv_id, entry_id, title, abstract, authors, primary_category, categories, comment, ' +
  'journal_ref, doi, published, updated, pdf_url, topics, classification_rationale, ' +
  'summary_short, summary_long, summary_conclusions';

// The same honest placeholder the (future) RAG endpoint will replace. Returned client-side so
// the browsing app needs no server at all until Q&A is built.
const ASK_PLACEHOLDER =
  "Q&A over the digest isn't available yet — retrieval-augmented answers over the indexed " +
  'papers are coming soon. In the meantime, browse the weekly issues and use the filters to ' +
  'find papers by topic, category, date, or keyword.';

// A `papers` row as returned by PostgREST: flat columns, summary split across three fields.
interface PaperRow {
  arxiv_id: string;
  entry_id: string;
  title: string;
  abstract: string;
  authors: { name: string; affiliation?: string | null }[];
  primary_category: string;
  categories: string[];
  comment: string | null;
  journal_ref: string | null;
  doi: string | null;
  published: string;
  updated: string;
  pdf_url: string;
  full_text?: string | null;
  topics: string[];
  classification_rationale: string | null;
  summary_short: string | null;
  summary_long: string | null;
  summary_conclusions: string | null;
}

/** The day after an inclusive `YYYY-MM-DD` upper bound, so `published < nextDay` includes it. */
function dayAfter(isoDate: string): string {
  const d = new Date(`${isoDate}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString();
}

/** Map a PostgREST row to a `Paper`, reassembling `summary` from its three columns. */
function rowToPaper(row: PaperRow): Paper {
  const summary =
    row.summary_short !== null
      ? {
          short: row.summary_short,
          long: row.summary_long ?? '',
          conclusions: row.summary_conclusions ?? '',
        }
      : undefined;
  return {
    arxiv_id: row.arxiv_id,
    entry_id: row.entry_id,
    title: row.title,
    abstract: row.abstract,
    authors: row.authors.map((a) => ({ name: a.name, affiliation: a.affiliation ?? undefined })),
    primary_category: row.primary_category,
    categories: row.categories,
    comment: row.comment ?? undefined,
    journal_ref: row.journal_ref ?? undefined,
    doi: row.doi ?? undefined,
    published: row.published,
    updated: row.updated,
    pdf_url: row.pdf_url,
    full_text: row.full_text ?? undefined,
    topics: row.topics,
    summary,
    classification_rationale: row.classification_rationale ?? undefined,
  };
}

export class SupabaseApiClient implements ApiClient {
  private readonly db: SupabaseClient;

  constructor(url: string, anonKey: string) {
    this.db = createClient(url, anonKey);
  }

  async listPapers(filters: PaperFilters = {}): Promise<Paper[]> {
    let query = this.db.from('papers').select(LIST_COLUMNS).order('published', { ascending: false });
    if (filters.topics?.length) query = query.overlaps('topics', filters.topics);
    if (filters.categories?.length) query = query.overlaps('categories', filters.categories);
    if (filters.from) query = query.gte('published', filters.from);
    if (filters.to) query = query.lt('published', dayAfter(filters.to));
    if (filters.q) {
      const needle = `%${filters.q}%`;
      query = query.or(`title.ilike.${needle},abstract.ilike.${needle}`);
    }
    const { data, error } = await query.returns<PaperRow[]>();
    if (error) throw new Error(`failed to list papers: ${error.message}`);
    return data.map(rowToPaper);
  }

  async getPaper(arxivId: string): Promise<Paper | null> {
    const { data, error } = await this.db
      .from('papers')
      .select(`${LIST_COLUMNS}, full_text`)
      .eq('arxiv_id', arxivId)
      .maybeSingle<PaperRow>();
    if (error) throw new Error(`failed to get paper ${arxivId}: ${error.message}`);
    return data ? rowToPaper(data) : null;
  }

  async listWeeks(): Promise<WeekSummary[]> {
    const { data, error } = await this.db
      .from('week_summaries')
      .select('week_key, count, start, end')
      .order('start', { ascending: false })
      .returns<{ week_key: string; count: number; start: string; end: string }[]>();
    if (error) throw new Error(`failed to list weeks: ${error.message}`);
    return data.map((row) => ({
      weekKey: row.week_key,
      label: weekLabel(row.start),
      count: row.count,
      start: row.start,
      end: row.end,
    }));
  }

  async getWeek(weekKey: string): Promise<WeekIssueData | null> {
    const { start, end } = weekKeyBounds(weekKey);
    const papers = await this.listPapers({ from: start.slice(0, 10), to: end.slice(0, 10) });
    if (papers.length === 0) return null;
    return {
      week: { weekKey, label: weekLabel(start), count: papers.length, start, end },
      papers,
    };
  }

  async getLatestWeek(): Promise<WeekIssueData | null> {
    const [latest] = await this.listWeeks();
    return latest ? this.getWeek(latest.weekKey) : null;
  }

  async listTopicsWithCounts(): Promise<TopicCount[]> {
    const { data, error } = await this.db
      .from('topic_counts')
      .select('topic, count')
      .returns<{ topic: string; count: number }[]>();
    if (error) throw new Error(`failed to count topics: ${error.message}`);
    const counts = new Map(data.map((row) => [row.topic, row.count]));
    // Order by the taxonomy, dropping topics no stored paper carries.
    return TOPICS.filter((title) => (counts.get(title) ?? 0) > 0).map((title) => ({
      title,
      count: counts.get(title) ?? 0,
    }));
  }

  async listCategories(): Promise<string[]> {
    const { data, error } = await this.db
      .from('category_list')
      .select('category')
      .order('category', { ascending: true })
      .returns<{ category: string }[]>();
    if (error) throw new Error(`failed to list categories: ${error.message}`);
    return data.map((row) => row.category);
  }

  async askDummy(): Promise<AskResponse> {
    // No server yet: return the honest placeholder (the question/scope args are ignored). The
    // real RAG endpoint lands as a serverless function later, and this method will call it.
    return { answer: ASK_PLACEHOLDER, citations: [] };
  }
}
