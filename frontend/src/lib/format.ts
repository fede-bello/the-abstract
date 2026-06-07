// Small presentational formatters. All dates rendered in UTC for stability.

import type { Author } from '@/data/types';

/** "Jun 4, 2026" */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  });
}

/** "2026-06-04" — for mono metadata. */
export function formatDateNumeric(iso: string): string {
  return iso.slice(0, 10);
}

/** "23 papers" / "1 paper" */
export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

/** Zero-padded index for numbered rows: 1 -> "01". */
export function indexLabel(n: number): string {
  return String(n).padStart(2, '0');
}

/** Author names truncated with "et al." past `max`. */
export function formatAuthors(authors: Author[], max = 4): string {
  const names = authors.map((a) => a.name);
  if (names.length <= max) return names.join(', ');
  return `${names.slice(0, max).join(', ')}, et al.`;
}

/** The first non-empty affiliation among authors, if any (a useful signal in the digest). */
export function leadAffiliation(authors: Author[]): string | undefined {
  return authors.find((a) => a.affiliation)?.affiliation;
}

/** Split a newline/bullet-delimited short summary into clean bullet strings. */
export function toBullets(short: string): string[] {
  return short
    .split('\n')
    .map((line) => line.replace(/^[-*•]\s*/, '').trim())
    .filter(Boolean);
}
