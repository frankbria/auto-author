import { readFileSync } from 'fs';
import { join } from 'path';

import {
  contrastRatio,
  oklchToken,
  themeBlock,
  WCAG_AA_NORMAL_TEXT,
} from './helpers/contrast';

/**
 * Second finding from #618, split out in #620: light-mode `--muted-foreground`
 * `#737373` on `--muted` `#f5f5f5` measured **4.34:1** in real axe-core output,
 * under the 4.5:1 AA floor for normal-weight body text. #618 routed around it by
 * using `text-foreground` for the chapter tab title, but the token pair itself
 * was unfixed — and `text-muted-foreground` is used on 65 components, plenty of
 * them carrying body text on a `bg-muted`/`bg-secondary`/`bg-accent` surface
 * (all the same `oklch(0.97)` in light, `oklch(0.269)` in dark).
 *
 * `--muted-foreground` is now `oklch(0.54)` in `:root` — `#6e6e6e`, 4.68:1 on
 * `--muted`. A five-step darkening, light theme only; every other pairing the
 * token appears in only improves.
 *
 * Like the #610 guard, this recomputes from the values actually in globals.css
 * rather than asserting a colour literal, so it fails if either half of the pair
 * is re-tuned. jsdom has no stylesheet, so jest-axe cannot see any of this.
 */

const GLOBALS_CSS = join(__dirname, '..', '..', 'app', 'globals.css');

// Every surface `text-muted-foreground` is painted on today. `muted`,
// `secondary` and `accent` share a value in both themes but are separate tokens
// and can drift apart, so each is checked on its own.
const SURFACES = ['background', 'card', 'muted', 'secondary', 'accent'] as const;
const THEMES = ['light', 'dark'] as const;

describe('muted-foreground clears WCAG 2.1 AA on every surface it lands on (#620)', () => {
  const css = readFileSync(GLOBALS_CSS, 'utf8');

  const cases = THEMES.flatMap((theme) =>
    SURFACES.map((surface) => [theme, surface] as const)
  );

  it.each(cases)('%s theme: is at least 4.5:1 on --%s', (theme, surface) => {
    const block = themeBlock(css, theme);
    const ratio = contrastRatio(
      oklchToken(block, 'muted-foreground'),
      oklchToken(block, surface)
    );

    expect(ratio).toBeGreaterThanOrEqual(WCAG_AA_NORMAL_TEXT);
  });

  it('reproduces the 4.34:1 figure axe-core reported for the old value', () => {
    // Pins the maths to the observed browser result rather than to arithmetic
    // this file also produced. oklch(0.556) was the pre-#620 light value.
    const beforeFix = contrastRatio(
      oklchToken('--x: oklch(0.556 0 0)', 'x'),
      oklchToken(themeBlock(css, 'light'), 'muted')
    );

    expect(beforeFix).toBeCloseTo(4.34, 1);
    expect(beforeFix).toBeLessThan(WCAG_AA_NORMAL_TEXT);
  });
});
