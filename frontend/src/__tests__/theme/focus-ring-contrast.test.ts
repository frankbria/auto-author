import { readFileSync } from 'fs';
import { join } from 'path';

import {
  WCAG_AA_NON_TEXT,
  compositeOver,
  contrastRatio,
  oklchToken,
  themeBlock,
} from './helpers/contrast';
import { FRONTEND_ROOT, shippedSources } from './helpers/sources';

/**
 * The focus ring clears WCAG 1.4.11 (3:1) on every surface a control sits on
 * (#697).
 *
 * Buttons, inputs, selects, textareas and badges pair `outline-none` with
 * `focus-visible:ring-ring/50`, so the `--ring` token *at the alpha the call
 * site writes* is the entire focus indicator. shadcn's `--ring` measured 1.54:1
 * at half strength — and nobody saw it, because Tailwind v3 emitted no rule for
 * `ring-ring/50` until #697 and those controls fell back to the default blue.
 *
 * The alphas come from the source rather than a constant: a call site written
 * as `ring-ring/30` is a weaker indicator, and the guard has to price that one.
 */

const css = readFileSync(join(FRONTEND_ROOT, 'src', 'app', 'globals.css'), 'utf8');

/** Every alpha `ring-ring` is used at in shipped source; bare `ring-ring` is 100. */
function ringAlphas(): number[] {
  const found = new Set<number>();
  for (const path of shippedSources()) {
    const source = readFileSync(join(FRONTEND_ROOT, path), 'utf8');
    for (const [, alpha] of source.matchAll(/(?<![\w-])ring-ring(?:\/(\d{1,3}))?(?![\w/-])/g)) {
      found.add(alpha ? Number(alpha) : 100);
    }
  }
  return [...found].sort((a, b) => a - b);
}

// The surfaces a focusable control is placed on: the page, cards and popovers
// (dialogs, menus), and the muted/secondary/accent panels.
const SURFACES = ['background', 'card', 'popover', 'muted', 'secondary', 'accent'];

const alphas = ringAlphas();
const cases = (['light', 'dark'] as const).flatMap((theme) =>
  alphas.flatMap((alpha) => SURFACES.map((surface) => [theme, alpha, surface] as const))
);

describe('focus ring contrast (#697)', () => {
  it('finds the ring alphas it is meant to be pricing', () => {
    // Vacuity guard: `/50` is the shape that hid the defect, so it must be in
    // the sweep, alongside the opaque form.
    expect(alphas).toEqual(expect.arrayContaining([50, 100]));
  });

  it.each(cases)('%s: ring-ring/%i on --%s is at least 3:1', (theme, alpha, surface) => {
    const block = themeBlock(css, theme);
    const surfaceRgb = oklchToken(block, surface);
    const ring = compositeOver(oklchToken(block, 'ring'), alpha / 100, surfaceRgb);
    expect(contrastRatio(ring, surfaceRgb)).toBeGreaterThanOrEqual(WCAG_AA_NON_TEXT);
  });
});
