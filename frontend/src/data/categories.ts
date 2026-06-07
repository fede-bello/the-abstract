// arXiv categories ingested by the pipeline, mirroring config.toml `arxiv_categories`.
// label is the human-readable expansion shown in tooltips / facet lists.
export interface ArxivCategory {
  code: string;
  label: string;
}

export const CATEGORIES: ArxivCategory[] = [
  { code: 'cs.LG', label: 'Machine Learning' },
  { code: 'cs.CL', label: 'Computation and Language' },
  { code: 'cs.CV', label: 'Computer Vision' },
  { code: 'cs.AI', label: 'Artificial Intelligence' },
  { code: 'cs.NE', label: 'Neural & Evolutionary Computing' },
  { code: 'stat.ML', label: 'Statistics / ML' },
  { code: 'math.OC', label: 'Optimization & Control' },
  { code: 'math.ST', label: 'Statistics Theory' },
];

export const CATEGORY_LABEL: Record<string, string> = Object.fromEntries(
  CATEGORIES.map((c) => [c.code, c.label]),
);
