import { execFileSync } from 'child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';

import { FRONTEND_ROOT, shippedSources } from './helpers/sources';

/**
 * Every opacity-modified colour class the app uses is actually emitted
 * (#682, widened in #697).
 *
 * The other guards in this directory read `tailwind.config.js` and
 * `globals.css` and do colour maths on what they find. None of them can see
 * whether Tailwind *generates a rule* for a class, and v3 silently generates
 * none for `<colour>/<n>` when it cannot parse the colour:
 *
 *   - #682: `destructive.DEFAULT: "var(--destructive)"` sent `bg-destructive/10`,
 *     `border-destructive/20`, `text-destructive/90` and `ring-destructive/20`
 *     to zero rules. The pre-PR review caught it; the channel form fixed it.
 *   - #697: the same was already true on `main` for every other `var()` token.
 *     `hover:bg-secondary/80` (secondary buttons had no hover), `ring-ring/50`
 *     (inputs focused in Tailwind's default blue), `bg-muted/50`, `bg-input/30`
 *     — 14 classes, none emitted, the whole theme suite green. This file only
 *     looked at `destructive`.
 *
 * So it now builds every `<prefix>-<colour>/<n>` class in shipped source.
 * "The config looks right" and "the CSS exists" are different claims, and only
 * the second one ships.
 */

const ALPHA_COLOUR_CLASS =
  /(?<![\w-])(?:bg|text|border(?:-[trblxy])?|ring|ring-offset|outline|fill|stroke|divide|from|via|to|placeholder|caret|accent|decoration)-[a-z]+(?:-[a-z]+)*(?:-\d{2,3})?\/\d{1,3}(?![\w/])/g;

/** Every opacity-modified colour class shape in shipped source. */
function alphaColourClasses(): string[] {
  const found = new Set<string>();
  for (const path of shippedSources()) {
    const source = readFileSync(join(FRONTEND_ROOT, path), 'utf8');
    for (const match of source.matchAll(ALPHA_COLOUR_CLASS)) found.add(match[0]);
  }
  return [...found].sort();
}

/** Build just these classes, against the real config, and return the CSS. */
function build(classes: string[]): string {
  const dir = mkdtempSync(join(tmpdir(), 'tw-alpha-'));
  try {
    const html = join(dir, 'probe.html');
    const input = join(dir, 'in.css');
    const output = join(dir, 'out.css');
    writeFileSync(html, `<div class="${classes.join(' ')}"></div>`, 'utf8');
    writeFileSync(input, '@tailwind utilities;\n', 'utf8');
    execFileSync(
      'npx',
      ['tailwindcss', '-i', input, '-o', output, '--content', html],
      { cwd: FRONTEND_ROOT, stdio: ['ignore', 'pipe', 'pipe'] }
    );
    return readFileSync(output, 'utf8');
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

/** Tailwind escapes `/` in a class name, so `bg-muted/50` is `.bg-muted\/50`. */
function selectorFor(className: string): string {
  return `.${className.replace(/\//g, '\\/')}`;
}

const classes = alphaColourClasses();
// One build, reused: there is no reason to pay for it per class.
const css = build(classes);

describe('opacity-modified colour utilities are emitted, not just configured (#682, #697)', () => {
  it('finds the classes it is meant to be checking', () => {
    // Vacuity guards. An empty or narrowed sweep passes the per-class check
    // while proving nothing, so pin both families that have regressed.
    expect(classes.length).toBeGreaterThanOrEqual(20);
    expect(classes.filter((c) => c.includes('-destructive')).length).toBeGreaterThanOrEqual(4);
    expect(classes).toEqual(expect.arrayContaining(['bg-secondary/80', 'ring-ring/50', 'bg-muted/50']));
  });

  it('builds a stylesheet at all', () => {
    // Separates "the build broke" from "a class is missing".
    expect(css.length).toBeGreaterThan(100);
  });

  it.each(classes)('emits a rule for %s', (className) => {
    expect(css).toContain(selectorFor(className));
  });
});
