// Frontend data types. These MIRROR the backend `Paper` model (snake_case kept on purpose so
// the future REST JSON maps 1:1 with no remapping layer). See backend clients/arxiv.py.

export interface Author {
  name: string;
  affiliation?: string;
}

export interface PaperSummary {
  /** 2–3 short bullet points (newline-separated), for quick scanning. */
  short: string;
  /** ~2 paragraphs: methodology, results, implications. */
  long: string;
  /** Brief significance / impact note. */
  conclusions: string;
}

export interface Paper {
  arxiv_id: string;
  entry_id: string; // canonical arXiv abstract URL
  title: string;
  abstract: string;
  authors: Author[];
  primary_category: string; // e.g. "cs.LG"
  categories: string[]; // all arXiv categories
  comment?: string;
  journal_ref?: string;
  doi?: string;
  published: string; // ISO datetime
  updated: string; // ISO datetime
  pdf_url: string;
  full_text?: string;
  topics: string[]; // display titles from the categorization taxonomy
  summary?: PaperSummary;
  classification_rationale?: string; // why this was kept as "useful"
}

/** Query parameters for listing papers — maps to the future GET /papers query string. */
export interface PaperFilters {
  topics?: string[];
  categories?: string[];
  from?: string; // ISO date (inclusive)
  to?: string; // ISO date (inclusive)
  q?: string; // keyword over title + abstract
}

/** A page window for paginated list queries (zero-based offset). */
export interface PageParams {
  limit: number;
  offset: number;
}

export interface TopicCount {
  title: string;
  count: number;
}

export interface WeekSummary {
  weekKey: string; // ISO week, e.g. "2026-W23"
  label: string; // human label, e.g. "Week of Jun 1, 2026"
  count: number;
  start: string; // ISO date (Monday)
  end: string; // ISO date (Sunday)
}

export interface WeekIssueData {
  week: WeekSummary;
  papers: Paper[];
}
