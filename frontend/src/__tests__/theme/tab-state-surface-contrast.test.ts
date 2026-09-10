import { readFileSync } from 'fs';
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

/**
 * #634, the mirror of #632. Where #632 banned dark translucent overlays with no
 * `dark:` prefix, this is the other half of the same bug class: an **opaque
 * light surface that was never given a dark counterpart**.
 *
 * `ChapterTab` painted its errored state as `border-red-200 bg-red-50` with no
 * `dark:` variant, while the text on top kept coming from theme tokens that do
 * flip. The result in dark theme was near-white text on a near-white card:
 *
 * | foreground on `bg-red-50` | light | dark |
 * |---|---|---|
 * | `--foreground` (inactive title) | 18.10 | **1.05** |
 * | `--muted-foreground` (close button) | 4.59 | **2.36** |
 * | `text-primary` (active title) | 5.75 | **2.73** |
 *
 * 1.05:1 is not low contrast, it is unreadable — on precisely the tab a user
 * needs to read. The active title is a third failing foreground the issue did
 * not name: the title span overrides the row's colour with `text-primary`.
 *
 * ## `text-primary` is not the `--primary` token
 *
 * It resolves to the theme-fixed brand indigo in `tailwind.config.js`
 * (`rgb(79, 70, 229)`), repainted `rgb(129, 140, 248)` in dark by #610's
 * `.dark .text-primary` override. The `--primary` oklch token feeds only the
 * v4-only `@theme` block, which this repo's Tailwind v3 ignores — so pricing
 * the active title as `--primary` measures a colour that never renders. It also
 * measures a *much* rosier one: an opaque `dark:bg-red-900` card would keep a
 * phantom near-white title at 7.95:1 while the real indigo-400 sat at 3.36:1,
 * under the floor this suite exists to enforce. Caught in review on this PR.
 *
 * `axe-core` cannot see any of this: jsdom carries no stylesheet, and the repo's
 * axe runs never render an errored tab. So the guard is static, reading the
 * class strings out of the component source in the style of
 * `status-dot-contrast.test.ts`.
 *
 * ## Which surface the dark card composites over
 *
 * The fix uses the `bg-<hue>-50 dark:bg-<hue>-900/NN` idiom the other nine red
 * surfaces in the tree already ship (#631). That dark card is translucent, so it
 * composites over whatever is *behind the tab* rather than over the tab's own
 * `bg-muted`/`bg-background` — `cn()` is `twMerge`, so the unprefixed
 * `bg-red-50` collides with and replaces the row's own unprefixed background,
 * leaving nothing under the translucent dark card but the parent.
 *
 * `SURFACES` is a deliberate superset of that parent: today every tab row sits
 * on `TabBar`'s `bg-background`, but `--card` and `--muted` are the other two
 * surfaces this component could be dropped onto, and asserting the worst case
 * over all three costs nothing and survives a re-parenting. It is not a claim
 * that all three are reachable now.
 */

const SRC = join(__dirname, '..', '..');
const GLOBALS_CSS = join(SRC, 'app', 'globals.css');
const CHAPTER_TAB = join(SRC, 'components', 'chapters', 'ChapterTab.tsx');

/**
 * The tab's conditional error/unsaved styling. `count` is the vacuity guard: if
 * the component is restructured and a constant stops matching, this says so
 * rather than sweeping nothing.
 */
const STATE_SOURCES = [
  { name: 'ERROR_TAB', pattern: /^const ERROR_TAB = '([^']+)'/gm, count: 1 },
  { name: 'UNSAVED_TAB', pattern: /^const UNSAVED_TAB = '([^']+)'/gm, count: 1 },
  { name: 'ERROR_ICON', pattern: /^const ERROR_ICON = '([^']+)'/gm, count: 1 },
] as const;

/** Surfaces a chapter tab row could sit on — see the doc comment. */
const SURFACES = ['background', 'card', 'muted'] as const;
const THEMES = ['light', 'dark'] as const;

/**
 * The *token* foregrounds on the errored tab: the row sets `text-foreground`
 * when active and `text-muted-foreground` when not, and the close button
 * re-declares `text-muted-foreground`.
 *
 * The two non-token foregrounds are asserted separately — the active title (see
 * `activeTitleColor`) and the alert glyph (`ERROR_ICON`, held to 1.4.11's 3:1
 * rather than 1.4.3's 4.5:1).
 */
const FOREGROUNDS = ['foreground', 'muted-foreground'] as const;

const TAILWIND_CONFIG = join(SRC, '..', 'tailwind.config.js');

/**
 * What `text-primary` actually paints. Read from the two files that decide it
 * rather than hardcoded, so removing #610's override fails here instead of
 * silently reverting this row to a 2.73:1 title.
 */
function activeTitleColor(theme: Theme, css: string): Rgb {
  if (theme === 'dark') {
    const override = css.match(
      /\.dark\s+\.text-primary[^{]*\{[^}]*color:\s*rgb\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)/
    );
    if (!override) throw new Error('globals.css has no `.dark .text-primary` rgb() override (#610)');
    return [Number(override[1]), Number(override[2]), Number(override[3])];
  }

  const config = readFileSync(TAILWIND_CONFIG, 'utf8');
  const brand = config.match(/primary:\s*\{\s*DEFAULT:\s*"rgb\((\d+),\s*(\d+),\s*(\d+)\)"/);
  if (!brand) throw new Error('tailwind.config.js has no `primary.DEFAULT` rgb()');
  return [Number(brand[1]), Number(brand[2]), Number(brand[3])];
}

/** Not a WCAG threshold — the drift floor #632 established for delimiters. */
const BORDER_VISIBLE = 1.2;

type Rgb = [number, number, number];
type Theme = (typeof THEMES)[number];

/**
 * A whole Tailwind colour utility. The property keeps its edge suffix, so
 * `border-t-red-200` and `dark:border-l-red-800` are not read as covering each
 * other. Arbitrary values (`bg-[#7f1d1d]`) deliberately do not match — see
 * `parse`.
 */
const CLASS =
  /^((?:[a-z0-9.[\]-]+:)*)(bg|border(?:-[trblxyse])?|text)-([a-z]+(?:-[a-z]+)*(?:-\d{2,3})?)(?:\/(\d+))?$/;

interface Utility {
  variants: string[];
  property: string;
  name: string;
  alpha: number;
}

/**
 * Every utility in a state class string.
 *
 * Throws on a token it cannot read rather than dropping it: a silently skipped
 * utility is how this guard would go green while the surface it is meant to
 * measure is still theme-blind. `themeBlindProperties('bg-[#7f1d1d]')` must not
 * come back empty.
 */
function parse(classes: string): Utility[] {
  return classes
    .trim()
    .split(/\s+/)
    .map((token) => {
      const match = token.match(CLASS);
      if (!match) throw new Error(`Unreadable colour utility \`${token}\` in \`${classes}\``);
      const [, variants, property, name, alpha] = match;
      return {
        variants: variants ? variants.split(':').filter(Boolean) : [],
        property,
        name,
        alpha: alpha ? Number(alpha) / 100 : 1,
      };
    });
}

/** Applies in the resting state of `theme`, as opposed to on hover/focus/group. */
function appliesIn(utility: Utility, theme: Theme): boolean {
  return theme === 'dark'
    ? utility.variants.length === 0 || (utility.variants.length === 1 && utility.variants[0] === 'dark')
    : utility.variants.length === 0;
}

/**
 * The bug class as a structural rule: an unprefixed colour utility is authored
 * for light and applies in *both* themes, so it needs a resting-state `dark:`
 * sibling on the same property. Returns the utilities that lack one.
 */
function themeBlindProperties(classes: string): string[] {
  const utilities = parse(classes);
  return [
    ...new Set(
      utilities
        .filter((u) => !u.variants.length)
        .filter(
          (u) =>
            !utilities.some(
              (other) =>
                other.variants.length === 1 &&
                other.variants[0] === 'dark' &&
                other.property === u.property
            )
        )
        .map((u) => `${u.property}-${u.name}`)
    ),
  ];
}

/** The utility that actually applies in `theme` for `property`, if any. */
function applicable(classes: string, property: string, theme: Theme): Utility | undefined {
  const utilities = parse(classes).filter((u) => u.property === property && appliesIn(u, theme));
  return theme === 'dark'
    ? (utilities.filter((u) => u.variants.length).pop() ?? utilities.pop())
    : utilities.pop();
}

/** A Tailwind palette literal or a `globals.css` token, composited if translucent. */
function resolve(utility: Utility, theme: Theme, over: Rgb, css: string): Rgb {
  const palette = utility.name.match(/^([a-z]+)-(\d{2,3})$/);
  const colour = palette
    ? hexToRgb((colors as unknown as Record<string, Record<string, string>>)[palette[1]][palette[2]])
    : oklchToken(themeBlock(css, theme), utility.name);

  return utility.alpha === 1 ? colour : compositeOver(colour, utility.alpha, over);
}

describe('ChapterTab state surfaces have a dark counterpart (#634)', () => {
  const css = readFileSync(GLOBALS_CSS, 'utf8');
  const source = readFileSync(CHAPTER_TAB, 'utf8');
  const token = (theme: Theme, name: string) => oklchToken(themeBlock(css, theme), name);

  const states = Object.fromEntries(
    STATE_SOURCES.map(({ name, pattern, count }) => {
      const found = [...source.matchAll(pattern)].map((m) => m[1]);
      // Vacuity guard — see STATE_SOURCES.
      expect({ name, count: found.length }).toEqual({ name, count });
      return [name, found[0]];
    })
  ) as Record<(typeof STATE_SOURCES)[number]['name'], string>;

  it('recognises a theme-blind surface and clears one with a dark counterpart', () => {
    // Anti-vacuity: once the component is fixed the sweep below passes whether
    // or not `themeBlindProperties` still works, so pin it to fixtures.
    expect(themeBlindProperties('border-red-200 bg-red-50')).toEqual(['border-red-200', 'bg-red-50']);
    expect(themeBlindProperties('bg-red-50 dark:bg-red-900/20')).toEqual([]);
    expect(themeBlindProperties('border-red-200 bg-red-50 dark:bg-red-900/20')).toEqual([
      'border-red-200',
    ]);
    expect(themeBlindProperties('dark:border-orange-700 border-orange-200')).toEqual([]);

    // A dark counterpart that only applies on hover does not cover the resting
    // state, and a different border edge is a different property.
    expect(themeBlindProperties('bg-red-50 hover:dark:bg-red-900/20')).toEqual(['bg-red-50']);
    expect(themeBlindProperties('border-t-red-200 dark:border-l-red-800')).toEqual([
      'border-t-red-200',
    ]);
    expect(themeBlindProperties('border-t-red-200 dark:border-t-red-800')).toEqual([]);

    // Loud, not silent: an arbitrary value this resolver cannot price must stop
    // the guard rather than be dropped as if it were theme-safe.
    expect(() => themeBlindProperties('bg-[#7f1d1d]')).toThrow(/Unreadable colour utility/);
  });

  it('resolves the resting-state utility, not a hover one', () => {
    const hoverOnly = 'bg-red-50 dark:bg-red-950 hover:dark:bg-red-800';
    expect(applicable(hoverOnly, 'bg', 'dark')?.name).toBe('red-950');
    expect(applicable(hoverOnly, 'bg', 'light')?.name).toBe('red-50');
  });

  it.each(Object.entries(states))('%s declares a dark counterpart for every colour', (_name, classes) => {
    expect(themeBlindProperties(classes)).toEqual([]);
  });

  const errorSurface = (theme: Theme, surface: (typeof SURFACES)[number]): Rgb => {
    const utility = applicable(states.ERROR_TAB, 'bg', theme);
    if (!utility) throw new Error(`No background utility in \`${states.ERROR_TAB}\` for ${theme}`);
    return resolve(utility, theme, token(theme, surface), css);
  };

  const borderOn = (classes: string, theme: Theme, surface: Rgb): number => {
    const border = applicable(classes, 'border', theme);
    if (!border) throw new Error(`No border utility in \`${classes}\` for ${theme}`);
    return contrastRatio(resolve(border, theme, surface, css), surface);
  };

  describe.each(THEMES)('%s theme', (theme) => {
    it.each(
      FOREGROUNDS.flatMap((fg) => SURFACES.map((surface) => [fg, surface] as const))
    )('--%s on the errored tab over --%s clears 4.5:1', (fg, surface) => {
      expect(contrastRatio(token(theme, fg), errorSurface(theme, surface))).toBeGreaterThanOrEqual(
        WCAG_AA_NORMAL_TEXT
      );
    });

    it.each(SURFACES)('the active title clears 4.5:1 on the errored tab over --%s', (surface) => {
      expect(
        contrastRatio(activeTitleColor(theme, css), errorSurface(theme, surface))
      ).toBeGreaterThanOrEqual(WCAG_AA_NORMAL_TEXT);
    });

    it.each(SURFACES)('the alert glyph clears 3:1 on the errored tab over --%s', (surface) => {
      // A 12px icon, not text: WCAG 2.1 1.4.11's 3:1 non-text floor. The tab's
      // readable label is held to 4.5:1 above.
      const icon = applicable(states.ERROR_ICON, 'text', theme);
      if (!icon) throw new Error(`No text utility in \`${states.ERROR_ICON}\` for ${theme}`);
      const card = errorSurface(theme, surface);
      expect(contrastRatio(resolve(icon, theme, card, css), card)).toBeGreaterThanOrEqual(
        WCAG_AA_NON_TEXT
      );
    });

    it.each(SURFACES)('the errored tab border stays visible over --%s', (surface) => {
      expect(borderOn(states.ERROR_TAB, theme, errorSurface(theme, surface))).toBeGreaterThan(
        BORDER_VISIBLE
      );
    });

    it.each(SURFACES)('the unsaved-changes border stays visible on --%s', (surface) => {
      // No background of its own: this state tints the tab's own surface.
      expect(borderOn(states.UNSAVED_TAB, theme, token(theme, surface))).toBeGreaterThan(
        BORDER_VISIBLE
      );
    });

    it.each(SURFACES)('errored *and* unsaved: the orange border stays visible over --%s', (surface) => {
      // Both flags is a reachable state, and `twMerge` resolves the `border-*`
      // collision in favour of `UNSAVED_TAB` (declared later in the `cn()` call)
      // while `ERROR_TAB` keeps the card — so the rendered pair is an orange
      // border on the red surface, which neither single-state case measures.
      expect(borderOn(states.UNSAVED_TAB, theme, errorSurface(theme, surface))).toBeGreaterThan(
        BORDER_VISIBLE
      );
    });
  });

  it.each([
    ['foreground', 1.05],
    ['muted-foreground', 2.36],
  ] as const)('reproduces dark --%s at %s:1 on the unfixed bg-red-50', (fg, expected) => {
    // Pins the maths to the figures measured for the bug rather than to
    // arithmetic this file also produced, the way #623 and #632 do.
    const beforeFix = contrastRatio(token('dark', fg), hexToRgb(colors.red[50]));

    expect(beforeFix).toBeCloseTo(expected, 1);
    expect(beforeFix).toBeLessThan(WCAG_AA_NORMAL_TEXT);
  });

  it('reproduces the active title at 2.73:1 on the unfixed bg-red-50', () => {
    // Not 1.15 — that was this guard pricing the title as the `--primary` token
    // before review caught that `text-primary` never paints it. The row was
    // failing either way, but at 2.73, and the fixed card gives 4.87 worst case
    // rather than the 11.53 the token model claimed.
    const beforeFix = contrastRatio(activeTitleColor('dark', css), hexToRgb(colors.red[50]));

    expect(beforeFix).toBeCloseTo(2.73, 1);
    expect(beforeFix).toBeLessThan(WCAG_AA_NORMAL_TEXT);
  });

  it('reproduces the alert glyph at 3.01:1, the margin the old text-red-600 had', () => {
    // Not a failure at the 3:1 non-text floor — which is the point: it cleared
    // by 0.01 with nothing pinning it. `text-red-400` gives 5.25 there.
    const beforeFix = contrastRatio(
      hexToRgb(colors.red[600]),
      compositeOver(hexToRgb(colors.red[900]), 0.2, token('dark', 'muted'))
    );

    expect(beforeFix).toBeCloseTo(3.01, 1);
    expect(beforeFix).toBeLessThan(WCAG_AA_NORMAL_TEXT);
  });
});
