import { readFileSync } from 'fs';
import { join } from 'path';

import { FRONTEND_ROOT } from './helpers/sources';

/**
 * Every `var(--x)` Tailwind v3 ships is declared somewhere v3 keeps.
 *
 * globals.css carries an `@theme inline { ... }` block that only Tailwind v4
 * understands; v3 passes it through as an unknown at-rule, so the `--color-*`
 * names it defines never exist at runtime. The base layer used to read three of
 * them. Each declaration was invalid at computed-value time and silently
 * dropped — the visible result was every unclassed `border` drawing in
 * `currentColor` (near-black in light) instead of `--border`.
 *
 * Nothing measured it: the contrast guards read token values, not whether the
 * rule that uses a token can resolve it.
 */

const css = readFileSync(join(FRONTEND_ROOT, 'src', 'app', 'globals.css'), 'utf8')
  .replace(/\/\*[\s\S]*?\*\//g, '');

// `@theme` holds declarations only, so the first `}` closes it.
const shipped = css.replace(/@theme\b[^{]*\{[^}]*\}/g, '');

const declared = new Set([...shipped.matchAll(/(--[\w-]+)\s*:/g)].map((m) => m[1]));
const referenced = [...new Set([...shipped.matchAll(/var\(\s*(--[\w-]+)/g)].map((m) => m[1]))];

describe('theme variables used by v3 are defined (#695)', () => {
  it('actually strips the v4-only @theme block and finds references', () => {
    // Vacuity guards. If the strip stops matching, `--color-*` names from @theme
    // count as declared and the check below passes while proving nothing.
    expect(css).toMatch(/@theme\b/);
    expect(shipped).not.toMatch(/@theme\b/);
    expect(referenced.length).toBeGreaterThanOrEqual(3);
  });

  it.each(referenced)('%s is declared outside @theme', (name) => {
    expect(declared).toContain(name);
  });
});
