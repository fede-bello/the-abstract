// Tiny subsequence fuzzy matcher — enough for a command palette over a few hundred items.
// Returns a score (higher = better) or null if the query isn't a subsequence of the text.

export function fuzzyScore(query: string, text: string): number | null {
  const q = query.trim().toLowerCase();
  if (!q) return 0;
  const t = text.toLowerCase();

  let score = 0;
  let ti = 0;
  let streak = 0;
  for (const char of q) {
    const found = t.indexOf(char, ti);
    if (found === -1) return null;
    // Reward consecutive matches and matches at word starts.
    streak = found === ti ? streak + 1 : 0;
    const atWordStart = found === 0 || t[found - 1] === ' ' || t[found - 1] === '-';
    score += 1 + streak * 2 + (atWordStart ? 3 : 0);
    ti = found + 1;
  }
  // Prefer shorter texts and earlier first matches.
  return score - t.length * 0.01;
}
