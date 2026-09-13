import { readFileSync } from 'fs';
import { join } from 'path';

import {
  contrastRatio,
  oklchToken,
  themeBlock,
  WCAG_AA_NORMAL_TEXT,
} from './helpers/contrast';
import { FRONTEND_ROOT } from './helpers/sources';

/**
 * #638. The issue reported that "every toast the app raises is a dark card on a
 * light page" because `ui/toaster.tsx` hardcodes `theme="dark"`.
 *
 * That file was never rendered. `app/layout.tsx` imports `ui/sonner.tsx`, which
 * already drives `theme` from `useTheme()` and already paints from tokens.
 * `ui/toaster.tsx` was a second, unused toaster — never imported in any commit —
 * and it is deleted, along with its rows in both theme ledgers.
 *
 * Deleting it removes the only thing that was watching this surface: those two
 * ledger rows were the only record that a toaster in this repo had ever been
 * theme-blind. So this guard replaces them, pointed at the toaster that actually
 * renders. Without it, someone hardcoding `theme="dark"` in `sonner.tsx`
 * tomorrow reproduces #638 exactly, with nothing to catch it — the "removing a
 * thing also removes its tripwire" shape this repo has hit before (#534, #630).
 *
 * Static, for the usual reason: jsdom carries no stylesheet, the toaster renders
 * into a portal only when a toast fires, and axe does not evaluate the icon
 * glyphs that carry severity here.
 */

const SONNER = join(FRONTEND_ROOT, 'src', 'components', 'ui', 'sonner.tsx');
const source = readFileSync(SONNER, 'utf8');

describe('the live toaster follows the app theme (#638)', () => {
  it('is the toaster the app actually renders', () => {
    // Pins the premise. If layout stops importing this file, the rest of this
    // guard is measuring something no user sees — which is exactly the mistake
    // #638 was written on.
    const layout = readFileSync(join(FRONTEND_ROOT, 'src', 'app', 'layout.tsx'), 'utf8');
    expect(layout).toMatch(/from '@\/components\/ui\/sonner'/);
    expect(layout).toMatch(/<SonnerToaster\s*\/>/);
  });

  it('takes its theme from useTheme, never a hardcoded value', () => {
    expect(source).toMatch(/useTheme\(\)/);
    expect(source).toMatch(/theme=\{theme as ToasterProps\["theme"\]\}/);

    // The #638 defect itself: a literal theme on the Sonner root pins every
    // toast to one appearance in both app themes.
    expect(source).not.toMatch(/theme="(light|dark)"/);
  });

  it('paints from theme tokens, not from fixed colours', () => {
    for (const [cssVar, token] of [
      ['--normal-bg', '--popover'],
      ['--normal-text', '--popover-foreground'],
      ['--normal-border', '--border'],
    ] as const) {
      expect(source).toContain(`"${cssVar}": "var(${token})"`);
    }

    // No neutral literal may reach this file. `bg-gray-900`/`text-gray-200` on
    // the deleted toaster is precisely what made it theme-blind, and it is what
    // its `gray-literal-baseline.json` row recorded.
    expect(source).not.toMatch(
      /(?:bg|text|border)-(?:gray|slate|zinc|neutral|stone)-\d{2,3}/
    );
    // Nor a dark translucent overlay — the other ledger row (#632).
    expect(source).not.toMatch(/(?:bg|border)-[a-z]+-(?:700|800|900)\/\d+/);
  });

  it('severity is carried by an icon, not by colour alone', () => {
    // WCAG 1.4.1: colour cannot be the sole indicator. The live toaster gives
    // each severity its own glyph, which is why it needs no per-severity tint —
    // and why deleting the four tints on the dead file loses nothing.
    for (const severity of ['success', 'info', 'warning', 'error', 'loading']) {
      expect(source).toMatch(new RegExp(`${severity}:\\s*<HugeiconsIcon`));
    }
  });
});

/**
 * The token pair the toast actually paints with, measured in both themes.
 *
 * #638's AC asked for every severity measured in both themes. The live toaster
 * sets no per-severity background or border, so there is one surface to measure,
 * not four: `--popover` with `--popover-foreground` on top, in each theme.
 */
describe('the toast surface clears WCAG in both themes (#638)', () => {
  const css = readFileSync(join(FRONTEND_ROOT, 'src', 'app', 'globals.css'), 'utf8');
  const token = (theme: 'light' | 'dark', name: string) =>
    oklchToken(themeBlock(css, theme), name);

  it.each(['light', 'dark'] as const)('%s: popover-foreground on popover clears 4.5:1', (theme) => {
    expect(
      contrastRatio(token(theme, 'popover-foreground'), token(theme, 'popover'))
    ).toBeGreaterThanOrEqual(WCAG_AA_NORMAL_TEXT);
  });

  it('reproduces the measured figures, so a token drift is visible here', () => {
    expect(
      contrastRatio(token('light', 'popover-foreground'), token('light', 'popover'))
    ).toBeCloseTo(19.8, 1);
    expect(
      contrastRatio(token('dark', 'popover-foreground'), token('dark', 'popover'))
    ).toBeCloseTo(17.18, 1);
  });
});
