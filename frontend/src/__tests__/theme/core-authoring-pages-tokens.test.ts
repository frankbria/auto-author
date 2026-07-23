import { readFileSync } from 'fs';
import { join } from 'path';

/**
 * Recurrence guard for #331 (P0.2): the book-detail, summary, and TOC-wizard
 * pages hardcoded near-white `text-gray-*` (plus `bg-gray-*`/`border-gray-*`)
 * directly on the theme-aware `bg-background`. The app ships a working light
 * theme (#64), so those elements dropped to ~1.1:1 contrast — invisible — and
 * the core authoring flow was unusable in light mode (WCAG 1.4.3).
 *
 * These are the exact pages the issue cites. A source sweep is the strongest
 * anti-recurrence guard: it catches ANY reintroduced gray literal across the
 * whole file (not just an element a render test happens to mount), including
 * the book-detail page whose full render is expensive to set up. Brand/semantic
 * accents (indigo/green/red) are intentionally theme-fixed here — same as the
 * #206 migration — so only the gray neutral family is banned.
 */

const FRONTEND_ROOT = join(__dirname, '..', '..', '..');

const PAGES = [
  'src/app/dashboard/books/[bookId]/page.tsx',
  'src/app/dashboard/books/[bookId]/summary/page.tsx',
  'src/components/toc/TocGenerationWizard.tsx',
];

// Matches theme-independent neutral literals like `text-gray-100`,
// `bg-gray-800/50`, `border-gray-700`.
const GRAY_LITERAL = /\b(?:text|bg|border)-gray-\d+/g;

describe('core authoring pages use theme tokens, not hardcoded grays (#331)', () => {
  it.each(PAGES)('%s contains no text/bg/border-gray literals', (relPath) => {
    const source = readFileSync(join(FRONTEND_ROOT, relPath), 'utf8');
    const matches = source.match(GRAY_LITERAL) ?? [];
    expect(matches).toEqual([]);
  });
});
