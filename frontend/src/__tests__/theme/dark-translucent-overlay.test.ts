import { existsSync, readFileSync } from 'fs';
import { join } from 'path';

import colors from 'tailwindcss/colors';

import {
  compositeOver,
  contrastRatio,
  hexToRgb,
  oklchToken,
  themeBlock,
  WCAG_AA_NON_TEXT,
  WCAG_AA_NORMAL_TEXT,
} from './helpers/contrast';
import { FRONTEND_ROOT, shippedSources } from './helpers/sources';

/**
 * #632, split out of #624 (PR #631). A **dark translucent overlay with no
 * `dark:` prefix** — `bg-<hue>-{700,800,900}/NN` — is by construction authored
 * for a dark page. #624 converted the TOC wizard and export page off `*-gray-N`
 * literals onto theme tokens, their surfaces turned light, and every accent
 * painted on such an overlay went to mud with them:
 *
 * | site                                          | before | after |
 * |-----------------------------------------------|--------|-------|
 * | `bg-yellow-900/20` + `text-yellow-400` icon   | 1.02:1 | 4.76  |
 * | `bg-green-900/30`  + `text-green-400` icon    | 1.05:1 | 4.79  |
 * | `bg-red-900/20`    + `text-red-400` icon      | 1.76:1 | 5.91  |
 *
 * Six of the eight failures #624 fixed were icon badges, and **axe reported zero
 * on every one** — its `color-contrast` rule does not evaluate non-text elements
 * at all, the same blind spot #623 hit with the status dots. So the guard is
 * static, not an axe run.
 *
 * ## The net, and what is deliberately outside it
 *
 * 700/800/900 only. A 400/500/600 translucent (`bg-amber-500/10`,
 * `bg-indigo-600/10`, `border-yellow-500/20` — all still in the tree) composites
 * to a *pale tint* on a light surface, not to mud, so it is not this bug class
 * and banning it would be a different, much larger change. Neutrals are excluded
 * because `core-authoring-pages-tokens.test.ts` already sweeps every `*-gray-N`
 * including translucent ones.
 *
 * The `dark:` check reads the whole variant chain, so `hover:dark:bg-red-800/70`
 * is fine and `dark:hover:bg-red-800/70` is too.
 *
 * ## The ledger
 *
 * `dark-overlay-baseline.json`, shaped like `gray-literal-baseline.json`:
 * per-distinct-overlay counts so a hue swap cannot net out, plus the stale-row
 * assertion #624 added, so a row the file no longer contains fails rather than
 * silently pre-authorising the overlay. Seventeen of the eighteen sites burn
 * down in this PR; the one ledgered file is there because its overlays are not
 * actually broken, for a reason the ledger states.
 *
 * (On the count: the issue's title says nineteen and its own file table sums to
 * fourteen. This sweep finds eighteen — the table missed `ui/toaster.tsx`
 * entirely, because its overlays carry a `group-[.toast]:` variant prefix that a
 * hand-written grep for an unprefixed class does not match. Which is the #620
 * lesson again: the sweep finds what the list forgets.)
 */

// A whole class token: any variant chain, then a colour utility on a non-neutral
// hue at a dark shade with an alpha suffix. The hue is a negative lookahead
// rather than a list so a palette addition is caught without editing this file.
const DARK_TRANSLUCENT =
  /((?:[a-z0-9.[\]-]+:)*)((?:bg|border|text|ring|from|via|to|shadow|divide|outline|fill|stroke|accent|caret|decoration)-(?!gray|slate|zinc|neutral|stone|white|black|transparent|current|inherit)[a-z]+-(?:700|800|900)\/\d+)/g;

/** Every unprefixed dark translucent overlay in `source`, as class strings. */
function unprefixedOverlays(source: string): string[] {
  return [...source.matchAll(DARK_TRANSLUCENT)]
    .filter(([, variants]) => !variants.split(':').includes('dark'))
    .map(([, , utility]) => utility);
}

interface BaselineEntry {
  /** Distinct overlay class → how many times this file may still contain it. */
  overlays: Record<string, number>;
  reason: string;
}

interface Baseline {
  _comment: string;
  files: Record<string, BaselineEntry>;
}

/** Every unprefixed dark translucent overlay in a shipped file, by class. */
function overlayCounts(relativePath: string): Record<string, number> {
  const source = readFileSync(join(FRONTEND_ROOT, relativePath), 'utf8');
  const counts: Record<string, number> = {};
  for (const utility of unprefixedOverlays(source)) {
    counts[utility] = (counts[utility] ?? 0) + 1;
  }
  return counts;
}

const baseline: Baseline = JSON.parse(
  readFileSync(join(FRONTEND_ROOT, 'dark-overlay-baseline.json'), 'utf8')
);
const sources = shippedSources();

describe('no theme-blind dark translucent overlays in shipped source (#632)', () => {
  it('recognises an unprefixed overlay and clears a `dark:`-prefixed one', () => {
    // The anti-vacuity assertion. Once the tree is clean, the sweep below passes
    // whether or not the pattern still works — a typo in `DARK_TRANSLUCENT` would
    // turn this whole file green forever. This pins the pattern to fixtures, so
    // breaking it fails here regardless of what the tree contains.
    expect(unprefixedOverlays('className="p-4 bg-red-900/20 border-red-700"')).toEqual([
      'bg-red-900/20',
    ]);
    expect(unprefixedOverlays('className="bg-red-50 dark:bg-red-900/20"')).toEqual([]);
    expect(unprefixedOverlays('className="hover:dark:bg-red-800/70"')).toEqual([]);
    expect(unprefixedOverlays('className="dark:hover:bg-red-800/70"')).toEqual([]);

    // Outside the net, on purpose — see the doc comment.
    expect(unprefixedOverlays('className="bg-amber-500/10 bg-indigo-600/10"')).toEqual([]);
    expect(unprefixedOverlays('className="bg-gray-800/50"')).toEqual([]);

    // Opaque `bg-red-900` is a different (and much commoner) shape; this guard
    // is only about translucency compositing over an unknown surface.
    expect(unprefixedOverlays('className="bg-red-900"')).toEqual([]);
  });

  it('sweeps the whole src tree, and never itself', () => {
    expect(sources.length).toBeGreaterThan(150); // 182 today
    expect(sources).toContain('src/components/errors/ErrorNotification.tsx');
    expect(sources).toContain('src/components/chapters/ChapterTabs.tsx');
    // This file quotes `bg-red-900/20` above; a sweep that included it would
    // match itself the moment it was tracked (the trap #620's guard documents).
    expect(sources).not.toContain('src/__tests__/theme/dark-translucent-overlay.test.ts');
  });

  it('has no unprefixed dark translucent overlay outside the ledger', () => {
    const offenders = sources
      .filter((path) => !(path in baseline.files))
      .flatMap((path) =>
        Object.keys(overlayCounts(path)).map((utility) => `${path} :: ${utility}`)
      );

    expect(offenders).toEqual([]);
  });

  it('has no ledgered file above its recorded count for any overlay', () => {
    const regressions = Object.entries(baseline.files).flatMap(([path, entry]) =>
      Object.entries(overlayCounts(path))
        .map(([utility, actual]) => ({
          path,
          utility,
          ledgered: entry.overlays[utility] ?? 0,
          actual,
        }))
        .filter(({ ledgered, actual }) => actual > ledgered)
    );

    expect(regressions).toEqual([]);
  });

  it('has no ledgered overlay the file no longer contains (#624)', () => {
    // The ledger's contract is "shrink freely, delete the row when it empties".
    // Without this, re-adding a row for a burned-down file passes — the ledger
    // being used to pre-authorise an overlay rather than to record one.
    const stale = Object.entries(baseline.files).flatMap(([path, entry]) => {
      const actual = overlayCounts(path);
      return Object.keys(entry.overlays)
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
      .filter(([, entry]) => !entry.reason?.trim() || !Object.keys(entry.overlays).length)
      .map(([path]) => path);
    expect(unexplained).toEqual([]);
  });
});

/**
 * The fix idiom, measured. Every one of the 14 conversions uses the pairs #631
 * established — `bg-<hue>-50 dark:bg-<hue>-900/NN`, `text-<hue>-700
 * dark:text-<hue>-400`, `border-<hue>-300 dark:border-<hue>-700` — so measuring
 * the idiom per hue covers all of them and pins the values a future edit must
 * beat.
 *
 * Measured against every surface one of these cards actually lands on. In light
 * the `-50` card is opaque so the surface behind it drops out; in dark the card
 * is translucent and composites over it, making `--muted` (the lightest of the
 * three) the worst case for the text on top.
 *
 * ## What is held to 4.5:1, and what is not
 *
 * The card's **text** is the binding obligation (WCAG 1.4.3) and it is asserted
 * at 4.5:1 — the idiom delivers 4.76–11.71 across both themes and all three
 * surfaces, so there is real headroom.
 *
 * The **border** and the card **tint** are not held to 1.4.11's 3:1, and they
 * would not survive it: `border-red-300` is 1.74:1 on `bg-red-50`, and the card
 * itself is 1.03–1.12:1 against the page. That is the shipped #631 idiom, and
 * it is correct here because every one of these surfaces is an alert that also
 * carries `role="alert"`, an icon, and literal text naming the condition
 * ("Error loading chapters", "Authentication Error"). Severity is never
 * conveyed by colour alone, so neither the border nor the tint is a sole
 * indicator, and 1.4.11 does not attach to it. Holding them to 3:1 anyway would
 * force a garish `border-<hue>-600` outline on every alert in the app for no
 * accessibility gain.
 *
 * What the border *is* held to is visibility: a delimiter that disappears into
 * its own card is a design regression even where it is not a WCAG failure. The
 * 1.2 floor sits just under yellow's 1.27, the tightest of the seven hues.
 */
describe('the #631/#632 fix idiom clears WCAG in both themes', () => {
  const css = readFileSync(join(FRONTEND_ROOT, 'src', 'app', 'globals.css'), 'utf8');
  const token = (theme: 'light' | 'dark', name: string) =>
    oklchToken(themeBlock(css, theme), name);
  const swatch = (hue: string, shade: number) =>
    hexToRgb((colors as unknown as Record<string, Record<string, string>>)[hue][shade]);

  /** Not a WCAG threshold — a drift guard, see the doc comment above. */
  const BORDER_VISIBLE = 1.2;

  // Light `--card`/`--popover` share `--background`'s white, so the distinct
  // light surfaces are white and `--muted`; in dark all three differ.
  const SURFACES = ['background', 'card', 'muted'] as const;

  // hue → the alpha its dark overlay is painted at, across the converted sites.
  const HUES = [
    ['red', 0.2],
    ['blue', 0.2],
    ['yellow', 0.2],
    ['orange', 0.2],
  ] as const;

  describe.each(HUES)('%s', (hue, alpha) => {
    it('light: -700 text on the opaque -50 card clears 4.5:1', () => {
      expect(contrastRatio(swatch(hue, 700), swatch(hue, 50))).toBeGreaterThanOrEqual(
        WCAG_AA_NORMAL_TEXT
      );
    });

    it.each(SURFACES)('dark: -400 text on -900/NN over --%s clears 4.5:1', (surface) => {
      const card = compositeOver(swatch(hue, 900), alpha, token('dark', surface));
      expect(contrastRatio(swatch(hue, 400), card)).toBeGreaterThanOrEqual(
        WCAG_AA_NORMAL_TEXT
      );
    });

    it('light: the -300 border stays visible against its own -50 card', () => {
      expect(contrastRatio(swatch(hue, 300), swatch(hue, 50))).toBeGreaterThan(
        BORDER_VISIBLE
      );
    });

    it.each(SURFACES)('dark: the -700 border stays visible on --%s', (surface) => {
      const card = compositeOver(swatch(hue, 900), alpha, token('dark', surface));
      expect(contrastRatio(swatch(hue, 700), card)).toBeGreaterThan(BORDER_VISIBLE);
    });
  });

  /**
   * The four ratios #624 measured in the browser, reproduced here.
   *
   * They reproduce over `--muted`, not `--background` — those badges sat on
   * `bg-muted`, and over white the same pairs give 1.10 / 1.91 / 1.03 / 1.02
   * instead. Worth spelling out: a contrast figure without the surface it was
   * taken against is not a measurement, and copying one out of an issue body
   * without re-deriving it is how #629 shipped two wrong numbers.
   */
  it.each([
    ['yellow badge', 'yellow', 400, 'yellow', 900, 0.2, 1.02],
    ['red badge', 'red', 400, 'red', 900, 0.2, 1.76],
    ['green badge', 'green', 400, 'green', 900, 0.3, 1.05],
    ['amber warning text', 'amber', 300, 'amber', 900, 0.2, 1.05],
  ] as const)(
    'reproduces the %s at %s:1 that #624 measured on bg-muted',
    (_label, fgHue, fgShade, bgHue, bgShade, alpha, expected) => {
      const beforeFix = contrastRatio(
        swatch(fgHue, fgShade),
        compositeOver(swatch(bgHue, bgShade), alpha, token('light', 'muted'))
      );

      expect(beforeFix).toBeCloseTo(expected, 1);
      expect(beforeFix).toBeLessThan(WCAG_AA_NON_TEXT);
    }
  );
});
