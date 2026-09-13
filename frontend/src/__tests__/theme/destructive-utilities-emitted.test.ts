import { execFileSync } from 'child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';

import { FRONTEND_ROOT, shippedSources } from './helpers/sources';

/**
 * The destructive utilities the app uses are actually emitted (#682).
 *
 * Every other guard in this directory reads `tailwind.config.js` and
 * `globals.css` and does colour maths on what it finds. None of them can see
 * whether Tailwind *generates a rule* for a class — and that is exactly the
 * regression the pre-PR review on #682 caught:
 *
 *   `destructive.DEFAULT: "var(--destructive)"` is theme-aware and measures
 *   perfectly, and makes Tailwind v3 stop emitting **every** opacity variant.
 *   `bg-destructive/10`, `border-destructive/20`, `text-destructive/90` and
 *   `ring-destructive/20` each went to **zero rules**. Error-card tints,
 *   invalid-state rings and destructive menu focus backgrounds would have
 *   silently lost their colour, with the whole theme suite green.
 *
 * The channel form — `rgb(var(--destructive-rgb) / <alpha-value>)` — keeps them.
 * This builds the stylesheet and checks, because "the config looks right" and
 * "the CSS exists" are different claims and only the second one ships.
 *
 * Deliberately narrow: it covers the destructive family, which is what #682
 * changed. Widening it to every token is a bigger job than the bug warrants and
 * would slow every run by a build.
 */

/** Every `<prefix>-destructive[/alpha]` class shape in shipped source. */
function destructiveClasses(): string[] {
  const found = new Set<string>();
  for (const path of shippedSources()) {
    const source = readFileSync(join(FRONTEND_ROOT, path), 'utf8');
    for (const match of source.matchAll(/\b(bg|text|border|ring|outline|fill|stroke)-destructive(-[a-z]+)?(\/\d+)?\b/g)) {
      found.add(match[0]);
    }
  }
  return [...found].sort();
}

/** Build just these classes and return the emitted CSS. */
function build(classes: string[]): string {
  const dir = mkdtempSync(join(tmpdir(), 'tw-destructive-'));
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

/** Tailwind escapes `/` in a class name, so `bg-destructive/10` is `.bg-destructive\/10`. */
function selectorFor(className: string): string {
  return `.${className.replace(/\//g, '\\/')}`;
}

describe('destructive utilities are emitted, not just configured (#682)', () => {
  const classes = destructiveClasses();
  // One build, reused: it costs ~150ms and there is no reason to pay it twice.
  const css = build(classes);

  it('finds the classes it is meant to be checking', () => {
    // Vacuity guard, and the one that matters most here: an empty list would
    // make the assertion below pass while proving nothing at all.
    expect(classes.length).toBeGreaterThanOrEqual(8);
    // The opacity variants are the whole point — a sweep that found only opaque
    // classes would miss the regression this file exists for.
    expect(classes.filter((c) => c.includes('/')).length).toBeGreaterThanOrEqual(4);
  });

  it('builds a stylesheet at all', () => {
    // A failed or empty build would make every `toContain` below fail for the
    // wrong reason; this separates "the build broke" from "a class is missing".
    expect(css.length).toBeGreaterThan(100);
  });

  it.each(destructiveClasses())('emits a rule for %s', (className) => {
    expect(css).toContain(selectorFor(className));
  });
});
