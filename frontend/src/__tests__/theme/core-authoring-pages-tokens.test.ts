import { readFileSync, readdirSync, existsSync } from 'fs';
import { join, relative, sep } from 'path';

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
 * `security-baseline.json` uses for advisories. Adding a gray literal anywhere,
 * including to a file already in the ledger, fails; burning one down does not.
 *
 * Sweeping the whole tree rather than the transitive import set from the core
 * authoring routes is deliberate: an import walk is exactly the mechanism that
 * can silently omit a file (dynamic imports especially), which is the defect
 * being fixed. Covering everything retires that caveat instead of documenting
 * around it.
 *
 * Test sources are out of scope — they aren't shipped UI, several legitimately
 * assert on gray class names, and this file's own doc comment above contains
 * `*-gray-N` literals, so a guard that scanned tests would match itself.
 */

const FRONTEND_ROOT = join(__dirname, '..', '..', '..');
const SRC_ROOT = join(FRONTEND_ROOT, 'src');
const BASELINE_PATH = join(FRONTEND_ROOT, 'gray-literal-baseline.json');

// Matches any theme-independent gray utility — `text-gray-100`,
// `bg-gray-800/50`, `border-gray-700`, and also `ring-gray-*`/`placeholder-gray-*`
// so a future reintroduction through a different utility can't slip past.
const GRAY_LITERAL = /\b[a-z-]*gray-\d+/g;

const IS_TEST_SOURCE = /(^|[\\/])(__tests__|__mocks__|e2e)[\\/]|\.(test|spec)\.[jt]sx?$/;
const IS_SOURCE = /\.tsx?$/;

interface BaselineEntry {
  count: number;
  reason: string;
}

interface Baseline {
  _comment: string;
  files: Record<string, BaselineEntry>;
}

/** Every shipped `.ts`/`.tsx` under `src/`, repo-relative and POSIX-separated. */
function shippedSources(dir: string = SRC_ROOT): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const absolute = join(dir, entry.name);
    const relativePath = relative(FRONTEND_ROOT, absolute).split(sep).join('/');

    if (entry.isDirectory()) return shippedSources(absolute);
    if (!IS_SOURCE.test(entry.name)) return [];
    if (IS_TEST_SOURCE.test(relativePath)) return [];
    return [relativePath];
  });
}

function grayLiteralCount(relativePath: string): number {
  const source = readFileSync(join(FRONTEND_ROOT, relativePath), 'utf8');
  return (source.match(GRAY_LITERAL) ?? []).length;
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
      .filter((path) => grayLiteralCount(path) > 0);

    expect(unledgered).toEqual([]);
  });

  it('has no ledgered file above its recorded count', () => {
    // A single test rather than `it.each`, which throws on an empty table —
    // i.e. it would break at the moment the ledger is finally burned down.
    const regressions = Object.entries(baseline.files)
      .map(([path, entry]) => ({ path, ledgered: entry.count, actual: grayLiteralCount(path) }))
      .filter(({ ledgered, actual }) => actual > ledgered);

    expect(regressions).toEqual([]);
  });

  it('ledgers only files that still exist, each with a reason', () => {
    const stale = Object.keys(baseline.files).filter(
      (path) => !existsSync(join(FRONTEND_ROOT, path))
    );
    expect(stale).toEqual([]);

    const unexplained = Object.entries(baseline.files)
      .filter(([, entry]) => !entry.reason?.trim())
      .map(([path]) => path);
    expect(unexplained).toEqual([]);
  });
});
