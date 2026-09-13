import { readFileSync } from 'fs';
import { join } from 'path';

import {
  colorToken,
  compositeOver,
  contrastRatio,
  themeBlock,
  WCAG_AA_NORMAL_TEXT,
} from './helpers/contrast';
import { FRONTEND_ROOT, shippedSources } from './helpers/sources';

/**
 * The destructive role needs two colours, and this pins both (#682).
 *
 * #682 was filed about the *button* — white on the brand red at 3.76:1, below AA
 * in every state including enabled, on two irreversible actions. Measuring the
 * fix turned up that the same value drove `text-destructive`, failing on **44
 * sites** nobody had ticketed: 3.76:1 on a light background, 3.45:1 on
 * `bg-muted`.
 *
 * The two uses pull opposite ways on a dark background. White needs a dark red
 * to sit on; red text needs a light one to sit on. red-700 is 6.47:1 under white
 * and 3.06:1 on `--background`; red-400 is 7.16:1 there and leaves white at
 * 2.24:1. No single value satisfies both, so there are two:
 *
 * - `destructive.DEFAULT` → `var(--destructive)`, red-700 in light and red-400
 *   in dark. Carries every text shape automatically.
 * - `destructive.surface` → red-700, theme-fixed. Four fill sites.
 *
 * **Why the token and not a `.dark .text-destructive` rule.** The first cut did
 * it with a stylesheet override, and the pre-PR review found what that misses:
 * `text-destructive/90` is a *different class*, and so are
 * `data-[variant=destructive]:text-destructive`,
 * `data-[variant=destructive]:focus:text-destructive`,
 * `data-[error=true]:text-destructive` and
 * `*:data-[slot=alert-description]:text-destructive/90`. A hand-written override
 * must name each one, and the next shape added silently misses — the #632 trap.
 * A theme-aware token has no such surface, which is why the override is gone.
 */

const GLOBALS = join(FRONTEND_ROOT, 'src', 'app', 'globals.css');
const TAILWIND = join(FRONTEND_ROOT, 'tailwind.config.js');

const WHITE: [number, number, number] = [255, 255, 255];

/** Every surface `text-destructive` is known to land on. */
const SURFACES = ['background', 'card', 'muted'] as const;

/** A literal `rgb(...)` under a key in `tailwind.config.js`'s destructive block. */
function configRgb(key: string): [number, number, number] {
  const config = readFileSync(TAILWIND, 'utf8');
  const block = config.match(/destructive:\s*\{([^}]*)\}/);
  if (!block) throw new Error('No `destructive` colour block in tailwind.config.js');
  const value = block[1].match(new RegExp(`${key}:\\s*"rgb\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)"`));
  if (!value) throw new Error(`\`destructive.${key}\` is not an rgb() literal`);
  return [Number(value[1]), Number(value[2]), Number(value[3])];
}

describe('the destructive role clears AA in both of its uses (#682)', () => {
  const css = readFileSync(GLOBALS, 'utf8');

  it('reads real values from the stylesheet and the config', () => {
    // Vacuity guard: a parse returning nothing would make every assertion below
    // pass over an empty set.
    const light = colorToken(themeBlock(css, 'light'), 'destructive-rgb');
    const dark = colorToken(themeBlock(css, 'dark'), 'destructive-rgb');
    expect(light).toHaveLength(3);
    expect(dark).toHaveLength(3);
    expect(light).not.toEqual(dark);
    expect(configRgb('surface')).toHaveLength(3);
  });

  it('keeps the token theme-aware rather than a literal', () => {
    // A literal here overrides the tokens and makes them inert, which is the
    // #634 trap and how this defect survived: globals.css already carried a
    // per-theme `--destructive` that nothing rendered.
    //
    // The *channel* form specifically. A plain `var(--destructive)` is
    // theme-aware but stops Tailwind v3 emitting every opacity variant —
    // `bg-destructive/10` and friends vanish silently, which the pre-PR review
    // caught and `destructive-utilities-emitted.test.ts` now proves.
    const config = readFileSync(TAILWIND, 'utf8');
    const block = config.match(/destructive:\s*\{([^}]*)\}/)![1];
    expect(block).toMatch(/DEFAULT:\s*"rgb\(var\(--destructive-rgb\) \/ <alpha-value>\)"/);
  });

  it.each(['light', 'dark'] as const)('is readable text on every %s surface', (theme) => {
    const block = themeBlock(css, theme);
    const fg = colorToken(block, 'destructive-rgb');
    for (const surface of SURFACES) {
      const ratio = contrastRatio(fg, colorToken(block, surface));
      expect({ theme, surface, clearsAA: ratio >= WCAG_AA_NORMAL_TEXT }).toEqual({
        theme,
        surface,
        clearsAA: true,
      });
    }
  });

  it('is readable on the tinted error card, which is the commonest shape', () => {
    // `bg-destructive/10 border-destructive/20 text-destructive` — the text sits
    // on a wash of its own colour, so the surface moves with the token and
    // measuring against the plain background would overstate it.
    for (const [theme, alpha] of [
      ['light', 0.1],
      ['dark', 0.2],
    ] as const) {
      const block = themeBlock(css, theme);
      const fg = colorToken(block, 'destructive-rgb');
      for (const surface of ['background', 'card'] as const) {
        const tinted = compositeOver(fg, alpha, colorToken(block, surface));
        expect(contrastRatio(fg, tinted)).toBeGreaterThanOrEqual(WCAG_AA_NORMAL_TEXT);
      }
    }
  });

  it('is readable at reduced opacity, which is a different class entirely', () => {
    // `text-destructive/90` and `*:data-[slot=alert-description]:text-destructive/90`
    // are the shapes the review caught a stylesheet override missing.
    for (const theme of ['light', 'dark'] as const) {
      const block = themeBlock(css, theme);
      const fg = colorToken(block, 'destructive-rgb');
      for (const surface of SURFACES) {
        const base = colorToken(block, surface);
        const ratio = contrastRatio(compositeOver(fg, 0.9, base), base);
        expect({ theme, surface, clearsAA: ratio >= WCAG_AA_NORMAL_TEXT }).toEqual({
          theme,
          surface,
          clearsAA: true,
        });
      }
    }
  });

  it('keeps white legible on the fill, in both themes', () => {
    // `destructive.surface` is theme-fixed precisely so this is one number.
    expect(contrastRatio(WHITE, configRgb('surface'))).toBeGreaterThanOrEqual(
      WCAG_AA_NORMAL_TEXT
    );
  });

  it('never paints a white label on the theme-aware token', () => {
    // The failure this architecture exists to prevent: `bg-destructive` with a
    // white label is 2.24:1 in dark. Opaque fills must use `-surface`.
    // `bg-destructive/10` and friends are tints *behind red text*, covered
    // above, and are fine.
    const offenders = shippedSources()
      .filter((path) => path.endsWith('.tsx'))
      .filter((path) =>
        /\bbg-destructive(?![-/\w])/.test(readFileSync(join(FRONTEND_ROOT, path), 'utf8'))
      );

    expect(offenders).toEqual([]);
  });

  it('recognises an opaque fill and clears a tint', () => {
    // Anti-vacuity for the sweep above: pins the pattern to fixtures, since a
    // typo in it would quietly pass over the whole tree.
    const opaque = /\bbg-destructive(?![-/\w])/;
    expect(opaque.test('hover:bg-destructive hover:text-destructive-foreground')).toBe(true);
    expect(opaque.test('bg-destructive/10 border-destructive/20')).toBe(false);
    expect(opaque.test('bg-destructive-surface text-white')).toBe(false);
  });
});
