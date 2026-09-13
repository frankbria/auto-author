import { existsSync, readFileSync } from 'fs';
import { join } from 'path';

import colors from 'tailwindcss/colors';

import {
  contrastRatio,
  hexToRgb,
  oklchToken,
  themeBlock,
  WCAG_AA_NON_TEXT,
  WCAG_AA_NORMAL_TEXT,
} from './helpers/contrast';
import { FRONTEND_ROOT, shippedSources } from './helpers/sources';

/**
 * #637, the other half of #632. Where #632 banned the **dark surface** with no
 * `dark:` prefix (`bg-<hue>-900/NN` authored for a dark page), this bans the
 * mirror: a **pale foreground** — `(text|border|ring|…)-<hue>-{200,300,400}` —
 * left stranded with nothing to swap it in the other theme.
 *
 * ## The predicate, and why the issue's version could not be used
 *
 * #637 proposes "pale hue utility with no `dark:` in its variant chain". That
 * over-matches by design rather than by accident: `border-red-300
 * dark:border-red-700` is the **correct** #631 idiom, and its light half has no
 * `dark:` prefix by construction. Sweeping on the issue's predicate flags 28
 * sites, of which **16 are that exact correct pair** — it would demand "fixing"
 * the pattern #631/#632 established, and the real defects would be lost in the
 * noise.
 *
 * The defect is being **stranded**: no `dark:`-prefixed use of the *same
 * property* anywhere in the class string. That is what leaves a dark-surface
 * accent painted on a light card with no counterpart. On the tree at the time of
 * writing that predicate finds 12, of which 4 were live light-mode failures.
 *
 * Comment lines are skipped. `ChapterTab.tsx` quotes `border-blue-400` inside a
 * #629 explanatory comment; matching prose would have put a guard row on a file
 * whose markup is clean.
 *
 * ## What was measured, and what it found
 *
 * | site | before | after |
 * |---|---|---|
 * | `summary` input error, `text-red-400` on white       | **2.77:1** | 6.47 |
 * | `summary` revert link, `text-indigo-400` on white    | **2.98:1** | 7.90 |
 * | `dashboard` header icon, `text-indigo-400` on white  | **2.98:1** | 7.90 |
 * | `edit-toc` add-subchapter hover, `text-indigo-400`   | **2.98:1** | 7.90 |
 *
 * The first two and the fourth are text (WCAG 1.4.3, 4.5:1). The third is a
 * 32px icon, so 1.4.11's 3:1 applies — and 2.98 misses it, which is the kind of
 * margin no eyeball review catches and axe never reports at all, since its
 * `color-contrast` rule does not evaluate non-text elements (the #623/#632 blind
 * spot).
 *
 * ## The ledger
 *
 * `stranded-accent-baseline.json`, shaped like `dark-overlay-baseline.json`:
 * per-distinct-utility counts so a hue swap cannot net out, plus the #624
 * stale-row assertion. Three kinds of entry are in it, each stating which:
 * theme-fixed error boundaries that must render without the theme system,
 * `disabled:` labels that WCAG 1.4.3 exempts as inactive components, and one
 * light-only toast whose real defect is #633-shaped.
 */

const PROPS =
  'text|border|ring|fill|stroke|divide|outline|decoration|caret|accent';
const NEUTRAL = 'gray|slate|zinc|neutral|stone|white|black|transparent|current|inherit';

/**
 * Variant chain, then a pale non-neutral colour utility with no alpha suffix.
 * Property and hue are captured separately because pairing is checked on BOTH —
 * see `strandedAccents`.
 */
const PALE_FOREGROUND = new RegExp(
  `((?:[a-z0-9.\\[\\]-]+:)*)((${PROPS})-(?!${NEUTRAL})([a-z]+)-(?:200|300|400))(?![/\\w-])`,
  'g'
);

const IS_COMMENT = /^\s*(\/\/|\*|\/\*)/;

/**
 * One quoted run per element's class list.
 *
 * Pairing is resolved **inside the string the accent sits in**, not across the
 * whole line, because two elements can share a source line. `chapters/
 * [chapterId]/page.tsx:41` is exactly that shape today — an outer
 * `className="… border-b"` and an inner `className="… border-blue-200
 * dark:border-blue-800 …"` on one line — so scoping to the line lets the inner
 * element's `dark:` counterpart rescue a stranded accent on the outer one. That
 * is the utility-pooling false green #635's guard shipped and its review caught;
 * this one is scoped so the same shape cannot arise.
 */
function classRuns(line: string): string[] {
  return line.match(/"[^"]*"|'[^']*'|`[^`]*`/g) ?? [];
}

/**
 * Every *stranded* pale foreground in `source`, as class strings.
 *
 * Pairing requires the same property **and the same hue**, within the same class
 * string. Mutation M1 caught what property-only pairing lets through: a stranded
 * `text-orange-400` on an alert row already carrying `dark:text-red-400` was
 * reported as paired because *some* `dark:text-` was present. Since a pale accent
 * is most likely to be added to exactly such a row, that made the guard quietly
 * useless in the commonest case.
 *
 * Known and accepted: a Prettier-wrapped `cn(...)` that splits a pair across two
 * string literals reports the light half as stranded. That is a **false positive**
 * — it fails loudly and is resolved by a ledger row or by keeping the pair
 * together — and is the right way round. A false green ships the bug; no shipped
 * file has that shape today (`TocSidebar.tsx:38` keeps its pair in one run).
 */
/** A variant chain as a comparable key, with `dark` removed. `""` = resting state. */
function stateKey(variants: string): string {
  return variants
    .split(':')
    .filter((v) => v && v !== 'dark')
    .sort()
    .join('|');
}

/** Every `dark:`-prefixed colour utility in a run, as `property-hue → stateKey[]`. */
function darkCounterparts(run: string): Map<string, string[]> {
  const found = new Map<string, string[]>();
  const ANY_COLOUR = new RegExp(
    `((?:[a-z0-9.\\[\\]-]+:)*)(${PROPS})-(?!${NEUTRAL})([a-z]+)-\\d+`,
    'g'
  );
  for (const [, variants, property, hue] of run.matchAll(ANY_COLOUR)) {
    if (!variants.split(':').includes('dark')) continue;
    const key = `${property}-${hue}`;
    found.set(key, [...(found.get(key) ?? []), stateKey(variants)]);
  }
  return found;
}

export function strandedAccents(source: string): string[] {
  return source.split('\n').flatMap((line) => {
    if (IS_COMMENT.test(line)) return [];
    return classRuns(line).flatMap((run) => {
      const counterparts = darkCounterparts(run);
      return [...run.matchAll(PALE_FOREGROUND)]
        .filter(([, variants]) => !variants.split(':').includes('dark'))
        .filter(([, variants, , property, hue]) => {
          // The counterpart must apply in the SAME state. `text-red-400
          // dark:hover:text-red-700` leaves the resting colour with no dark
          // replacement in its actual state, and `hover:text-indigo-400
          // dark:focus:…` likewise — both reported clean before this check.
          const states = counterparts.get(`${property}-${hue}`) ?? [];
          return !states.includes(stateKey(variants));
        })
        .map(([, , utility]) => utility);
    });
  });
}

interface BaselineEntry {
  /** Distinct stranded utility → how many times this file may still contain it. */
  utilities: Record<string, number>;
  reason: string;
}

interface Baseline {
  _comment: string;
  files: Record<string, BaselineEntry>;
}

function strandedCounts(relativePath: string): Record<string, number> {
  const source = readFileSync(join(FRONTEND_ROOT, relativePath), 'utf8');
  const counts: Record<string, number> = {};
  for (const utility of strandedAccents(source)) {
    counts[utility] = (counts[utility] ?? 0) + 1;
  }
  return counts;
}

const baseline: Baseline = JSON.parse(
  readFileSync(join(FRONTEND_ROOT, 'stranded-accent-baseline.json'), 'utf8')
);
const sources = shippedSources();

describe('no stranded pale accents in shipped source (#637)', () => {
  it('flags a stranded accent and clears a properly paired one', () => {
    // The anti-vacuity assertion. Once the tree is clean the sweep below passes
    // whether or not the pattern still works, so a typo in PALE_FOREGROUND would
    // turn this file green forever. These fixtures pin the pattern itself.
    expect(strandedAccents('className="text-red-400 text-xs"')).toEqual(['text-red-400']);
    expect(strandedAccents('className="text-indigo-400"')).toEqual(['text-indigo-400']);

    // The correct #631 idiom — the light half is unprefixed BY DESIGN. This is
    // the case the issue's proposed predicate would have failed on, 16 times.
    expect(strandedAccents('className="border-red-300 dark:border-red-700"')).toEqual([]);
    expect(strandedAccents('className="text-red-700 dark:text-red-400"')).toEqual([]);

    // Pairing is per-property: a dark: border does not rescue a stranded text.
    expect(strandedAccents('className="text-red-400 dark:border-red-700"')).toEqual([
      'text-red-400',
    ]);

    // ...and per-HUE. Mutation M1's exact shape: a stranded orange on an alert row
    // that is otherwise a correct red pair. Property-only pairing passed this.
    expect(
      strandedAccents(
        'className="text-orange-400 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400"'
      )
    ).toEqual(['text-orange-400']);

    // ...and per class RUN. Two elements on one source line must not pool their
    // utilities: the inner element's `dark:text-red-400` does not rescue the
    // outer element's stranded `text-red-400`. This is the false green #635's
    // guard shipped, and the tree has the two-elements-one-line shape today
    // (`chapters/[chapterId]/page.tsx:41`).
    expect(
      strandedAccents(
        '<div className="text-red-400"><span className="text-red-700 dark:text-red-400">x</span></div>'
      )
    ).toEqual(['text-red-400']);

    // Whole variant chain is read, either order.
    expect(strandedAccents('className="hover:dark:text-red-400"')).toEqual([]);
    expect(strandedAccents('className="dark:hover:text-red-400"')).toEqual([]);

    // The counterpart must apply in the SAME state (found by codex review).
    // A dark: class in a *different* state leaves the pale colour with no
    // replacement where it actually paints. Both of these were clean before.
    expect(strandedAccents('className="text-red-400 dark:hover:text-red-700"')).toEqual([
      'text-red-400',
    ]);
    expect(
      strandedAccents('className="hover:text-indigo-400 dark:focus:text-indigo-700"')
    ).toEqual(['text-indigo-400']);
    // ...and the matching-state pair still clears, in either order. This is the
    // shape of this PR's own edit-toc fix.
    expect(
      strandedAccents('className="hover:text-indigo-400 dark:hover:text-indigo-700"')
    ).toEqual([]);
    expect(
      strandedAccents('className="hover:text-indigo-400 hover:dark:text-indigo-700"')
    ).toEqual([]);
    // A non-dark variant does NOT exempt it — a hover-only pale accent is still
    // stranded, which is exactly what edit-toc/page.tsx:471 was.
    expect(strandedAccents('className="hover:text-indigo-400"')).toEqual([
      'text-indigo-400',
    ]);

    // Outside the net on purpose: neutrals belong to
    // core-authoring-pages-tokens.test.ts; alpha suffixes belong to #632; 500+
    // shades are not pale-authored.
    expect(strandedAccents('className="text-gray-400"')).toEqual([]);
    expect(strandedAccents('className="border-red-300/50"')).toEqual([]);
    expect(strandedAccents('className="text-red-500 text-red-600"')).toEqual([]);
    // Background is not a foreground; a pale bg is not this bug.
    expect(strandedAccents('className="bg-red-300"')).toEqual([]);

    // Prose, not markup.
    expect(strandedAccents('  // #629: was a hand-rolled border-blue-400 ring')).toEqual([]);
    expect(strandedAccents('   * | `bg-yellow-900/20` + `text-yellow-400` |')).toEqual([]);
  });

  it('sweeps the whole src tree, and never itself', () => {
    expect(sources.length).toBeGreaterThan(150); // 181 today
    expect(sources).toContain('src/app/dashboard/page.tsx');
    expect(sources).toContain('src/components/toc/TocReview.tsx');
    // This file quotes `text-red-400` throughout; a sweep including it would
    // match itself the moment it was tracked (the #620 trap).
    expect(sources).not.toContain('src/__tests__/theme/stranded-light-accent.test.ts');
  });

  it('has no stranded pale accent outside the ledger', () => {
    const offenders = sources
      .filter((path) => !(path in baseline.files))
      .flatMap((path) =>
        Object.keys(strandedCounts(path)).map((utility) => `${path} :: ${utility}`)
      );

    expect(offenders).toEqual([]);
  });

  it('has no ledgered file above its recorded count for any utility', () => {
    const regressions = Object.entries(baseline.files).flatMap(([path, entry]) =>
      Object.entries(strandedCounts(path))
        .map(([utility, actual]) => ({
          path,
          utility,
          ledgered: entry.utilities[utility] ?? 0,
          actual,
        }))
        .filter(({ ledgered, actual }) => actual > ledgered)
    );

    expect(regressions).toEqual([]);
  });

  it('has no ledgered utility the file no longer contains (#624)', () => {
    // "Shrink freely, delete the row when it empties." Without this, re-adding a
    // row for a burned-down file passes — the ledger pre-authorising a class
    // rather than recording one.
    const stale = Object.entries(baseline.files).flatMap(([path, entry]) => {
      const actual = strandedCounts(path);
      return Object.keys(entry.utilities)
        .filter((utility) => !(utility in actual))
        .map((utility) => `${path} :: ${utility}`);
    });

    expect(stale).toEqual([]);
  });

  it('ledgers only files that still exist, each with a reason', () => {
    const missing = Object.keys(baseline.files).filter(
      (path) => !existsSync(join(FRONTEND_ROOT, path))
    );
    expect(missing).toEqual([]);

    const unexplained = Object.entries(baseline.files)
      .filter(([, entry]) => !entry.reason?.trim() || !Object.keys(entry.utilities).length)
      .map(([path]) => path);
    expect(unexplained).toEqual([]);
  });
});

/**
 * The four conversions, measured on the surface each actually lands on.
 *
 * Light `--background` and `--card` are both white in this theme, so one figure
 * covers both; the dark halves composite over nothing (these are opaque text
 * colours on the dark page surface), so `--background` is the surface there.
 *
 * A ratio without the surface it was taken against is not a measurement — the
 * repo has shipped two wrong numbers by copying figures out of an issue body
 * (#629), and a colour that never renders (#634's `text-primary`), so every
 * value below is derived here from `globals.css` and the Tailwind palette.
 */
describe('the #637 conversions clear WCAG in both themes', () => {
  const css = readFileSync(join(FRONTEND_ROOT, 'src', 'app', 'globals.css'), 'utf8');
  const token = (theme: 'light' | 'dark', name: string) =>
    oklchToken(themeBlock(css, theme), name);
  const swatch = (hue: string, shade: number) =>
    hexToRgb((colors as unknown as Record<string, Record<string, string>>)[hue][shade]);

  it.each([
    ['red', 'summary input error'],
    ['indigo', 'summary revert link / edit-toc hover'],
  ] as const)('light: %s-700 on white clears 4.5:1 (%s)', (hue, _site) => {
    expect(
      contrastRatio(swatch(hue, 700), token('light', 'background'))
    ).toBeGreaterThanOrEqual(WCAG_AA_NORMAL_TEXT);
  });

  it.each([
    ['red', 'summary input error'],
    ['indigo', 'summary revert link / edit-toc hover'],
  ] as const)('dark: %s-400 on the dark page clears 4.5:1 (%s)', (hue, _site) => {
    expect(
      contrastRatio(swatch(hue, 400), token('dark', 'background'))
    ).toBeGreaterThanOrEqual(WCAG_AA_NORMAL_TEXT);
  });

  it('the dashboard header icon clears 1.4.11 in both themes', () => {
    // A 32px icon is a non-text graphic: 3:1, not 4.5:1. It is called out
    // separately because indigo-400's 2.98:1 missed this by 0.02 — the margin
    // that makes a static guard worth having.
    expect(
      contrastRatio(swatch('indigo', 700), token('light', 'background'))
    ).toBeGreaterThanOrEqual(WCAG_AA_NON_TEXT);
    expect(
      contrastRatio(swatch('indigo', 400), token('dark', 'background'))
    ).toBeGreaterThanOrEqual(WCAG_AA_NON_TEXT);
  });

  /** The four failures this PR fixes, reproduced so a regression is recognisable. */
  it.each([
    ['summary input error text-red-400 on white', 'red', 400, 2.77],
    ['summary revert link text-indigo-400 on white', 'indigo', 400, 2.98],
    ['dashboard header icon text-indigo-400 on white', 'indigo', 400, 2.98],
  ] as const)('reproduces the %s failure at %s:1', (_label, hue, shade, expected) => {
    const before = contrastRatio(swatch(hue, shade), token('light', 'background'));
    expect(before).toBeCloseTo(expected, 1);
    expect(before).toBeLessThan(WCAG_AA_NORMAL_TEXT);
  });

  it('the ledgered exemptions are what the ledger says they are', () => {
    // The ledger's reasons carry numbers; if they drift, the reasons become
    // fiction. These pin the three that justify an exemption on a measurement.
    expect(contrastRatio(swatch('red', 400), swatch('gray', 900))).toBeCloseTo(6.41, 1);
    expect(contrastRatio(swatch('red', 400), swatch('gray', 950))).toBeCloseTo(7.28, 1);
    expect(contrastRatio(swatch('indigo', 400), swatch('indigo', 800))).toBeCloseTo(3.33, 1);
    expect(contrastRatio(swatch('green', 400), swatch('green', 800))).toBeCloseTo(4.09, 1);
    // VoiceTextInput's toast: fine in light, #633-shaped in dark.
    expect(contrastRatio(swatch('green', 800), swatch('green', 50))).toBeCloseTo(6.81, 1);
    expect(
      contrastRatio(swatch('green', 800), token('dark', 'background'))
    ).toBeLessThan(WCAG_AA_NORMAL_TEXT);
  });
});
