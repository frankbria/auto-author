import { readFileSync } from 'fs';
import { join } from 'path';

import colors from 'tailwindcss/colors';

import {
  contrastRatio,
  hexToRgb,
  oklchToken,
  themeBlock,
  WCAG_AA_NON_TEXT,
} from './helpers/contrast';

/**
 * #623, split out of #620. Chapter status is encoded as a `rounded-full` dot
 * whose colour is the only at-a-glance signal — the label lives in a tooltip,
 * and the tab's `aria-label` is `Open chapter {title}`. That makes the dot a
 * non-text UI component under WCAG 2.1 1.4.11, whose floor is 3:1.
 *
 * `axe-core`'s `color-contrast` rule does not check non-text elements at all, so
 * a clean axe run is vacuous here. The dots are also Tailwind palette literals
 * rather than theme tokens, so this reads the classes out of the component
 * sources and resolves them against the surfaces in `globals.css`, per theme.
 *
 * The failure it locks down: `bg-green-500` (COMPLETED) was **2.09:1** on light
 * `bg-muted`. The thin passes — `blue-500` at 3.37 light-muted, `purple-500` at
 * 3.82 dark-muted — are covered by the same sweep so they cannot drift under.
 */

const SRC = join(__dirname, '..', '..');
const GLOBALS_CSS = join(SRC, 'app', 'globals.css');

/**
 * Every place a status dot's colour is declared. `count` is a vacuity guard: if
 * a file is restructured and the pattern stops matching, the test says so rather
 * than silently sweeping nothing.
 */
const DOT_SOURCES = [
  { file: 'components/chapters/ChapterTab.tsx', pattern: /^\s*color: '([^']+)'/gm, count: 4 },
  { file: 'components/ui/ChapterStatusIndicator.tsx', pattern: /^\s*color: '([^']+)'/gm, count: 4 },
  { file: 'components/chapters/MobileChapterTabs.tsx', pattern: /return '(bg-[^']+)'/g, count: 5 },
] as const;

// The surfaces a status dot is ever painted on. Light `--card`/`--popover` share
// `--background`'s value, and the dark sheet/tab surfaces share `--muted`'s.
const SURFACES = ['background', 'muted'] as const;
const THEMES = ['light', 'dark'] as const;

/**
 * Picks the utility that actually applies in `theme` from a class string, then
 * resolves it to sRGB. Tailwind palette literals come from tailwind's own
 * palette; `bg-<token>` utilities come from globals.css.
 */
function dotColor(
  classes: string,
  theme: 'light' | 'dark',
  css: string
): [number, number, number] {
  const utilities = classes.trim().split(/\s+/).filter((c) => /(^|:)bg-/.test(c));
  const applicable =
    theme === 'dark'
      ? (utilities.filter((c) => c.startsWith('dark:')).pop() ??
         utilities.filter((c) => !c.includes(':')).pop())
      : utilities.filter((c) => !c.includes(':')).pop();

  if (!applicable) throw new Error(`No background utility in \`${classes}\` for ${theme}`);
  const name = applicable.replace(/^dark:/, '').replace(/^bg-/, '');

  const palette = name.match(/^([a-z]+)-(\d{2,3})$/);
  if (palette) {
    const [, hue, shade] = palette;
    const scale = colors[hue as keyof typeof colors];
    const value = typeof scale === 'object' ? (scale as Record<string, string>)[shade] : undefined;
    if (!value) throw new Error(`No Tailwind colour \`${name}\``);
    return hexToRgb(value);
  }

  return oklchToken(themeBlock(css, theme), name);
}

describe('chapter status dots clear WCAG 2.1 1.4.11 on every surface (#623)', () => {
  const css = readFileSync(GLOBALS_CSS, 'utf8');

  const dots = DOT_SOURCES.flatMap(({ file, pattern, count }) => {
    const source = readFileSync(join(SRC, file), 'utf8');
    const found = [...source.matchAll(pattern)].map((m) => m[1]);

    // Vacuity guard — see DOT_SOURCES.
    expect({ file, count: found.length }).toEqual({ file, count });

    return found.map((classes) => ({ file, classes }));
  });

  const cases = dots.flatMap(({ file, classes }) =>
    THEMES.flatMap((theme) =>
      SURFACES.map((surface) => [file, classes, theme, surface] as const)
    )
  );

  it.each(cases)('%s `%s`: %s theme is at least 3:1 on --%s', (_file, classes, theme, surface) => {
    const ratio = contrastRatio(
      dotColor(classes, theme, css),
      oklchToken(themeBlock(css, theme), surface)
    );

    expect(ratio).toBeGreaterThanOrEqual(WCAG_AA_NON_TEXT);
  });

  it('reproduces the 2.09:1 figure measured for the old bg-green-500', () => {
    // Pins the maths to the #623 measurement rather than to arithmetic this file
    // also produced, the way the #610 and #620 guards do.
    const beforeFix = contrastRatio(
      hexToRgb(colors.green[500]),
      oklchToken(themeBlock(css, 'light'), 'muted')
    );

    expect(beforeFix).toBeCloseTo(2.09, 1);
    expect(beforeFix).toBeLessThan(WCAG_AA_NON_TEXT);
  });
});
