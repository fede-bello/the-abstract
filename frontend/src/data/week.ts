// ISO-week helpers. A weekly "issue" is not stored anywhere — it is derived by grouping
// papers by the ISO week of their `published` date. All math is done in UTC for stability.

import type { Paper, WeekSummary, WeekIssueData } from './types';

const DAY_MS = 24 * 60 * 60 * 1000;

function toUTCDate(iso: string): Date {
  const d = new Date(iso);
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
}

/** Day index with Monday = 0 … Sunday = 6. */
function mondayIndex(d: Date): number {
  return (d.getUTCDay() + 6) % 7;
}

/** ISO week-numbering year + week for a date. */
function isoWeekParts(d: Date): { year: number; week: number } {
  const target = new Date(d);
  target.setUTCDate(target.getUTCDate() - mondayIndex(target) + 3); // nearest Thursday
  const firstThursday = new Date(Date.UTC(target.getUTCFullYear(), 0, 4));
  firstThursday.setUTCDate(firstThursday.getUTCDate() - mondayIndex(firstThursday) + 3);
  const week = 1 + Math.round((target.getTime() - firstThursday.getTime()) / (7 * DAY_MS));
  return { year: target.getUTCFullYear(), week };
}

/** "2026-W23" for an ISO datetime string. */
export function isoWeekKey(iso: string): string {
  const { year, week } = isoWeekParts(toUTCDate(iso));
  return `${year}-W${String(week).padStart(2, '0')}`;
}

/** Monday (start) and Sunday (end) bounding the ISO week that contains `iso`. */
export function weekBounds(iso: string): { start: string; end: string } {
  const d = toUTCDate(iso);
  const monday = new Date(d.getTime() - mondayIndex(d) * DAY_MS);
  const sunday = new Date(monday.getTime() + 6 * DAY_MS);
  return { start: monday.toISOString(), end: sunday.toISOString() };
}

/** "Week of Jun 1, 2026" from an ISO date (the week's Monday). */
export function weekLabel(startIso: string): string {
  const d = new Date(startIso);
  const month = d.toLocaleString('en-US', { month: 'short', timeZone: 'UTC' });
  return `Week of ${month} ${d.getUTCDate()}, ${d.getUTCFullYear()}`;
}

function summaryFor(weekKey: string, sample: Paper, count: number): WeekSummary {
  const { start, end } = weekBounds(sample.published);
  return { weekKey, label: weekLabel(start), count, start, end };
}

/** Group papers into week issues, newest week first; papers within sorted newest first. */
export function groupByWeek(papers: Paper[]): WeekIssueData[] {
  const byWeek = new Map<string, Paper[]>();
  for (const paper of papers) {
    const key = isoWeekKey(paper.published);
    const bucket = byWeek.get(key);
    if (bucket) bucket.push(paper);
    else byWeek.set(key, [paper]);
  }

  const issues: WeekIssueData[] = [];
  for (const [weekKey, group] of byWeek) {
    const sorted = [...group].sort((a, b) => b.published.localeCompare(a.published));
    const first = sorted[0];
    if (!first) continue;
    issues.push({ week: summaryFor(weekKey, first, sorted.length), papers: sorted });
  }

  return issues.sort((a, b) => b.week.weekKey.localeCompare(a.week.weekKey));
}
