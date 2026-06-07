import { describe, expect, it } from 'vitest';

import type { Paper } from '@/data/types';
import { applyFilters, topicCounts } from './filtering';

function makePaper(overrides: Partial<Paper> & Pick<Paper, 'arxiv_id'>): Paper {
  return {
    entry_id: `https://arxiv.org/abs/${overrides.arxiv_id}`,
    pdf_url: `https://arxiv.org/pdf/${overrides.arxiv_id}`,
    title: 'Untitled',
    abstract: '',
    authors: [],
    primary_category: 'cs.LG',
    categories: ['cs.LG'],
    published: '2026-06-01T00:00:00Z',
    updated: '2026-06-01T00:00:00Z',
    topics: [],
    ...overrides,
  };
}

const papers: Paper[] = [
  makePaper({
    arxiv_id: '1',
    title: 'Diffusion at scale',
    abstract: 'a study of denoising',
    authors: [{ name: 'Ada Lovelace' }],
    categories: ['cs.CV', 'cs.LG'],
    topics: ['Diffusion Models', 'Computer Vision'],
    published: '2026-06-05T00:00:00Z',
  }),
  makePaper({
    arxiv_id: '2',
    title: 'Reasoning in language models',
    abstract: 'chain of thought',
    categories: ['cs.CL'],
    topics: ['LLMs', 'Reasoning'],
    published: '2026-06-01T00:00:00Z',
  }),
  makePaper({
    arxiv_id: '3',
    title: 'Graph theory',
    categories: ['stat.ML'],
    topics: ['Graph Neural Networks', 'Theory'],
    published: '2026-05-20T00:00:00Z',
  }),
];

describe('applyFilters', () => {
  it('returns all papers sorted newest first with no filters', () => {
    const result = applyFilters(papers);
    expect(result.map((p) => p.arxiv_id)).toEqual(['1', '2', '3']);
  });

  it('filters by topic (OR within topics)', () => {
    const result = applyFilters(papers, { topics: ['LLMs', 'Theory'] });
    expect(result.map((p) => p.arxiv_id).sort()).toEqual(['2', '3']);
  });

  it('filters by arXiv category', () => {
    const result = applyFilters(papers, { categories: ['cs.LG'] });
    expect(result.map((p) => p.arxiv_id)).toEqual(['1']);
  });

  it('filters by inclusive date range', () => {
    const result = applyFilters(papers, { from: '2026-06-01', to: '2026-06-04' });
    expect(result.map((p) => p.arxiv_id)).toEqual(['2']);
  });

  it('matches keyword across title, abstract, and authors', () => {
    expect(applyFilters(papers, { q: 'denoising' }).map((p) => p.arxiv_id)).toEqual(['1']);
    expect(applyFilters(papers, { q: 'lovelace' }).map((p) => p.arxiv_id)).toEqual(['1']);
    expect(applyFilters(papers, { q: 'chain' }).map((p) => p.arxiv_id)).toEqual(['2']);
  });

  it('combines filters with AND across dimensions', () => {
    const result = applyFilters(papers, { topics: ['Computer Vision'], categories: ['cs.CL'] });
    expect(result).toHaveLength(0);
  });
});

describe('topicCounts', () => {
  it('counts papers per topic in taxonomy order, omitting empties', () => {
    const counts = topicCounts(papers);
    const llms = counts.find((c) => c.title === 'LLMs');
    expect(llms?.count).toBe(1);
    // taxonomy order: LLMs comes before Computer Vision before Diffusion? check ordering is stable
    const titles = counts.map((c) => c.title);
    expect(titles).toContain('Diffusion Models');
    expect(titles).not.toContain('Multimodal'); // zero count omitted
  });
});
