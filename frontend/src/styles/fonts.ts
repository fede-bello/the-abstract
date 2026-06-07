// Side-effect imports: self-host the three typefaces via fontsource (no external requests,
// better for an OSS app). Imported once from main.tsx.
//
// Display: Archivo (variable) — bold grotesque for mastheads/headlines.
// Body:    Hanken Grotesk (variable) — humanist grotesque, distinct from the display.
// Mono:    Space Mono — numbered index rows, counts, dates, arXiv ids, category badges.
import '@fontsource-variable/archivo';
import '@fontsource-variable/hanken-grotesk';
import '@fontsource/space-mono/400.css';
import '@fontsource/space-mono/700.css';
