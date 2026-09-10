import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

import { FRONTEND_ROOT, shippedSources } from './helpers/sources';

/**
 * Recurrence guard for #331 (P0.2): the book-detail, summary, and TOC-wizard
 * pages hardcoded near-white `text-gray-*` (plus `bg-gray-*`/`border-gray-*`)
 * directly on the theme-aware `bg-background`. The app ships a working light
 * theme (#64), so those elements dropped to ~1.1:1 contrast — invisible — and
 * the core authoring flow was unusable in light mode (WCAG 1.4.3).
 *
 * Brand/semantic accents (indigo/green/red) are intentionally theme-fixed here
 * — same as the #206 migration — so only the gray neutral family is banned.
 *
 * ## Why this sweeps everything (#620)
 *
 * Until #620 this guard walked a hand-maintained `PAGES` array. That list is
 * what let #618 ship a 1.46:1 label: `ChapterTab.tsx` was simply not on it, and
 * neither was a single child step of `TocGenerationWizard` even though the
 * wizard shell itself was. A list you have to remember to edit is not a guard.
 *
 * So the sweep is now every shipped source file under `src/`, with the known
 * offenders ledgered in `gray-literal-baseline.json` — the same shape
 * `security-baseline.json` uses for advisories. Adding a gray literal anywhere
 * fails; burning one down does not.
 *
 * The ledger records a count *per distinct literal*, not one total per file. A
 * single total would let a swap through: drop one `text-gray-500`, add one
 * `text-gray-300`, and the sum is unchanged — which is precisely the wrong-shade
 * edit that shipped #618. Per-literal counts fail on that.
 *
 * Sweeping the whole tree rather than the transitive import set from the core
 * authoring routes is deliberate: an import walk is exactly the mechanism that
 * can silently omit a file (dynamic imports especially), which is the defect
 * being fixed. Covering everything retires that caveat instead of documenting
 * around it.
 *
 * Test sources are out of scope — they aren't shipped UI, several legitimately
 * assert on gray class names, and this file's own doc comment above contains
 * `*-gray-N` literals, so a guard that scanned tests would match itself. That
 * walk now lives in `helpers/sources.ts`, shared with the #632 overlay guard so
 * the two cannot disagree about which files are shipped.
 */

const BASELINE_PATH = join(FRONTEND_ROOT, 'gray-literal-baseline.json');

// Matches any theme-independent gray utility — `text-gray-100`,
// `bg-gray-800/50`, `border-gray-700`, and also `ring-gray-*`/`placeholder-gray-*`
// so a future reintroduction through a different utility can't slip past.
const GRAY_LITERAL = /\b[a-z-]*gray-\d+/g;

interface BaselineEntry {
  /** Distinct gray literal → how many times this file may still contain it. */
  literals: Record<string, number>;
  reason: string;
}

interface Baseline {
  _comment: string;
  files: Record<string, BaselineEntry>;
}

function grayLiteralCounts(relativePath: string): Record<string, number> {
  const source = readFileSync(join(FRONTEND_ROOT, relativePath), 'utf8');
  const counts: Record<string, number> = {};
  for (const literal of source.match(GRAY_LITERAL) ?? []) {
    counts[literal] = (counts[literal] ?? 0) + 1;
  }
  return counts;
}

function grayLiteralTotal(relativePath: string): number {
  return Object.values(grayLiteralCounts(relativePath)).reduce((a, b) => a + b, 0);
}

const baseline: Baseline = JSON.parse(readFileSync(BASELINE_PATH, 'utf8'));
const sources = shippedSources();

describe('shipped source uses theme tokens, not hardcoded grays (#331, #620)', () => {
  it('sweeps the whole src tree, so no file can be silently omitted', () => {
    // Guards the guard: if the walk breaks (bad filter, wrong root) it would
    // pass vacuously against an empty file list.
    expect(sources.length).toBeGreaterThan(150); // 182 today
    expect(sources).toContain('src/components/toc/TocReview.tsx');
    expect(sources).toContain('src/components/chapters/ChapterTab.tsx');
    expect(sources).not.toContain(
      'src/__tests__/theme/core-authoring-pages-tokens.test.ts'
    );
  });

  it('has no gray literals outside the ledger', () => {
    const unledgered = sources
      .filter((path) => !(path in baseline.files))
      .filter((path) => grayLiteralTotal(path) > 0);

    expect(unledgered).toEqual([]);
  });

  it('has no ledgered file above its recorded count for any literal', () => {
    // A single test rather than `it.each`, which throws on an empty table —
    // i.e. it would break at the moment the ledger is finally burned down.
    const regressions = Object.entries(baseline.files).flatMap(([path, entry]) =>
      Object.entries(grayLiteralCounts(path))
        .map(([literal, actual]) => ({
          path,
          literal,
          ledgered: entry.literals[literal] ?? 0,
          actual,
        }))
        .filter(({ ledgered, actual }) => actual > ledgered)
    );

    expect(regressions).toEqual([]);
  });

  it('has no ledgered literal the file no longer contains (#624)', () => {
    // The ledger's contract is "shrink freely, delete the entry when it empties".
    // Nothing enforced the second half: re-adding a row for a burned-down file
    // passed, which is the ledger being used to *pre-authorise* a literal rather
    // than to record one — exactly what its own `_comment` forbids. A row whose
    // actual count is zero is provably stale, so it must go. Partial shrink is
    // still free: a row of 5 against an actual 2 is fine and does not fail here.
    const stale = Object.entries(baseline.files).flatMap(([path, entry]) => {
      const actual = grayLiteralCounts(path);
      return Object.keys(entry.literals)
        .filter((literal) => !(literal in actual))
        .map((literal) => `${path} :: ${literal}`);
    });

    expect(stale).toEqual([]);
  });

  it('ledgers only files that still exist, each with a reason', () => {
    const stale = Object.keys(baseline.files).filter(
      (path) => !existsSync(join(FRONTEND_ROOT, path))
    );
    expect(stale).toEqual([]);

    const unexplained = Object.entries(baseline.files)
      .filter(([, entry]) => !entry.reason?.trim() || !Object.keys(entry.literals).length)
      .map(([path]) => path);
    expect(unexplained).toEqual([]);
  });
});
