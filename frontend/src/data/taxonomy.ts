// The categorization taxonomy — display titles, mirroring backend
// steps/categorization/step.py (PaperTopics). The single source of truth for filter facets.
// Order matches the backend: topical concerns first, then transversal methods.
export const TOPICS = [
  'LLMs',
  'NLP',
  'Computer Vision',
  'Multimodal',
  'Speech & Audio',
  'Diffusion Models',
  'Generative Models',
  'Graph Neural Networks',
  'Reinforcement Learning',
  'Agents',
  'Reasoning',
  'Retrieval & RAG',
  'Time Series',
  'Model Architectures',
  'Representation Learning',
  'AI for Science',
  'Optimization',
  'Efficient ML',
  'Theory',
  'Safety & Alignment',
  'Interpretability',
  'Benchmarks & Datasets',
] as const;

export type Topic = (typeof TOPICS)[number];
