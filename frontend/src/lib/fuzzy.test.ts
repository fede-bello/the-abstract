import { describe, expect, it } from 'vitest';

import { fuzzyScore } from './fuzzy';

describe('fuzzyScore', () => {
  it('returns 0 for an empty query (everything matches)', () => {
    expect(fuzzyScore('', 'anything')).toBe(0);
  });

  it('returns null when the query is not a subsequence', () => {
    expect(fuzzyScore('xyz', 'diffusion models')).toBeNull();
  });

  it('matches a subsequence regardless of gaps', () => {
    expect(fuzzyScore('dm', 'diffusion models')).not.toBeNull();
  });

  it('is case-insensitive', () => {
    expect(fuzzyScore('LLM', 'llms')).not.toBeNull();
  });

  it('scores a prefix higher than a scattered match', () => {
    const prefix = fuzzyScore('diff', 'diffusion models') ?? -Infinity;
    const scattered = fuzzyScore('diff', 'distributed inference for flow') ?? -Infinity;
    expect(prefix).toBeGreaterThan(scattered);
  });

  it('rewards word-start matches', () => {
    const wordStart = fuzzyScore('gm', 'generative models') ?? -Infinity;
    const midWord = fuzzyScore('gm', 'segment') ?? -Infinity;
    expect(wordStart).toBeGreaterThan(midWord);
  });
});
