// Pure, testable keyword/facet filtering. BrowsePage applies the keyword filter client-side
// (deferred) over papers the API already filtered by topic/category/date. No React, no I/O.

import type { Paper, PaperFilters } from '@/data/types';

function matchesKeyword(paper: Paper, q: string): boolean {
  const needle = q.trim().toLowerCase();
  if (!needle) return true;
  const haystack = `${paper.title} ${paper.abstract} ${paper.authors
    .map((a) => a.name)
    .join(' ')}`.toLowerCase();
  return haystack.includes(needle);
}

function matchesTopics(paper: Paper, topics: string[]): boolean {
  if (topics.length === 0) return true;
  return topics.some((t) => paper.topics.includes(t));
}

function matchesCategories(paper: Paper, categories: string[]): boolean {
  if (categories.length === 0) return true;
  return categories.some((c) => paper.categories.includes(c));
}

function matchesDateRange(paper: Paper, from?: string, to?: string): boolean {
  const day = paper.published.slice(0, 10);
  if (from && day < from) return false;
  if (to && day > to) return false;
  return true;
}

/** Apply all filters; returns papers newest first. */
export function applyFilters(papers: Paper[], filters: PaperFilters = {}): Paper[] {
  const { topics = [], categories = [], from, to, q = '' } = filters;
  return papers
    .filter(
      (p) =>
        matchesTopics(p, topics) &&
        matchesCategories(p, categories) &&
        matchesDateRange(p, from, to) &&
        matchesKeyword(p, q),
    )
    .sort((a, b) => b.published.localeCompare(a.published));
}
