import { describe, expect, it } from 'vitest';

import type { Paper } from './types';
import { groupByWeek, isoWeekKey, weekBounds, weekLabel } from './week';

function paperOn(id: string, published: string): Paper {
  return {
    arxiv_id: id,
    entry_id: '',
    pdf_url: '',
    title: id,
    abstract: '',
    authors: [],
    primary_category: 'cs.LG',
    categories: ['cs.LG'],
    published,
    updated: published,
    topics: [],
  };
}

describe('isoWeekKey', () => {
  it('computes the ISO week for a mid-week date', () => {
    // Mon 2026-06-01 falls in ISO week 23 of 2026.
    expect(isoWeekKey('2026-06-03T10:00:00Z')).toBe('2026-W23');
  });

  it('pads single-digit weeks', () => {
    expect(isoWeekKey('2026-01-08T00:00:00Z')).toMatch(/^2026-W0\d$/);
  });

  it('assigns the same key to every day in one ISO week', () => {
    const monday = isoWeekKey('2026-06-01T00:00:00Z');
    const sunday = isoWeekKey('2026-06-07T23:00:00Z');
    expect(monday).toBe(sunday);
  });
});

describe('weekBounds', () => {
  it('returns Monday..Sunday bounding the date', () => {
    const { start, end } = weekBounds('2026-06-04T12:00:00Z');
    expect(start.slice(0, 10)).toBe('2026-06-01'); // Monday
    expect(end.slice(0, 10)).toBe('2026-06-07'); // Sunday
  });
});

describe('weekLabel', () => {
  it('formats the week-of label', () => {
    expect(weekLabel('2026-06-01T00:00:00Z')).toBe('Week of Jun 1, 2026');
  });
});

describe('groupByWeek', () => {
  const papers = [
    paperOn('a', '2026-06-05T00:00:00Z'),
    paperOn('b', '2026-06-02T00:00:00Z'),
    paperOn('c', '2026-05-20T00:00:00Z'),
  ];

  it('groups into weekly issues, newest week first', () => {
    const issues = groupByWeek(papers);
    expect(issues).toHaveLength(2);
    expect(issues[0]?.week.weekKey).toBe('2026-W23');
    expect(issues[0]?.week.count).toBe(2);
    expect(issues[1]?.week.weekKey).toBe('2026-W21');
  });

  it('sorts papers within a week newest first', () => {
    const issues = groupByWeek(papers);
    expect(issues[0]?.papers.map((p) => p.arxiv_id)).toEqual(['a', 'b']);
  });

  it('returns an empty array for no papers', () => {
    expect(groupByWeek([])).toEqual([]);
  });
});
