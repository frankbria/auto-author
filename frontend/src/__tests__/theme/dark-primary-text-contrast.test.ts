import { readFileSync } from 'fs';
import { join } from 'path';

import {
  contrastRatio,
  oklchToken,
  themeBlock,
  WCAG_AA_NORMAL_TEXT,
} from './helpers/contrast';

/**
 * Recurrence guard for #610 (P2.27): `text-primary` is the theme-fixed brand
 * indigo-600 (`tailwind.config.js` → `primary.DEFAULT`), and on the dark
 * `--card` surface that is 2.85:1 — below the 4.5:1 WCAG 2.1 AA floor for
 * normal-weight body text. It shipped on the active header nav link, i.e. on
 * every authenticated page. `globals.css` now lightens the *text* role to
 * indigo-400 under `.dark`.
 *
 * This recomputes the ratio from the values actually in `globals.css` rather
 * than asserting a colour literal, so it also fails if someone re-tunes the
 * dark surface tokens out from under the override. jsdom carries no stylesheet
 * and no layout, so `jest-axe` cannot see any of this — a `color-contrast`
 * scan there would be vacuous. This is the real guard; the axe scans in
 * `accessibility/ComponentAccessibilityAudit.test.tsx` cover structure only.
 *
 * The oklch→sRGB conversion lives in `./helpers/contrast` and is validated
 * against a real browser: it reproduces axe-core's reported `#171717`
 * background and `2.85` ratio from the issue.
 */

const GLOBALS_CSS = join(__dirname, '..', '..', 'app', 'globals.css');

/** The colour globals.css gives `text-primary` under `.dark`. */
function darkPrimaryTextColor(css: string): [number, number, number] {
  const rule = css.match(/\.dark\s+\.text-primary[^{]*\{([^}]*)\}/);
  if (!rule) throw new Error('globals.css has no `.dark .text-primary` colour override');

  const rgb = rule[1].match(/color:\s*rgb\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)/);
  if (!rgb) throw new Error('The `.dark .text-primary` override is not an rgb() colour');
  return [Number(rgb[1]), Number(rgb[2]), Number(rgb[3])];
}

// The dark surfaces `text-primary` is actually painted on today: the sticky
// header and mobile drawer (`bg-card`), page bodies and the active chapter tab
// (`bg-background`), and the mobile nav hover state (`bg-accent`).
const DARK_SURFACES = ['card', 'background', 'accent'] as const;

describe('text-primary clears WCAG 2.1 AA on the dark surfaces (#610)', () => {
  const css = readFileSync(GLOBALS_CSS, 'utf8');

  it.each(DARK_SURFACES)('is at least 4.5:1 on --%s', (token) => {
    const ratio = contrastRatio(
      darkPrimaryTextColor(css),
      oklchToken(themeBlock(css, 'dark'), token)
    );

    expect(ratio).toBeGreaterThanOrEqual(WCAG_AA_NORMAL_TEXT);
  });

  it('also lightens the hover state, which out-specifies the base override', () => {
    // `.dark .text-primary` is (0,2,0); Tailwind's own `.hover\:text-primary:hover`
    // is also (0,2,0) but emitted later, so the inactive header links would keep
    // failing on hover unless the override names that selector too.
    expect(css).toMatch(/\.dark\s+\.hover\\:text-primary:hover/);
  });

  it('leaves bg-primary alone, whose white foreground needs the darker indigo', () => {
    // Re-theming the shared `primary` token instead would make `bg-primary`
    // indigo-400, and white on indigo-400 is 2.98:1 — a new AA failure.
    const config = readFileSync(join(__dirname, '..', '..', '..', 'tailwind.config.js'), 'utf8');
    const white: [number, number, number] = [255, 255, 255];
    const brand = config.match(/primary:\s*\{\s*DEFAULT:\s*"rgb\((\d+),\s*(\d+),\s*(\d+)\)"/);
    if (!brand) throw new Error('No `primary.DEFAULT` rgb() in tailwind.config.js');

    const ratio = contrastRatio(white, [
      Number(brand[1]),
      Number(brand[2]),
      Number(brand[3]),
    ]);

    expect(ratio).toBeGreaterThanOrEqual(WCAG_AA_NORMAL_TEXT);
  });
});
