import { readFileSync } from 'fs';
import { join } from 'path';

import {
  compositeOver,
  contrastRatio,
  oklchToken,
  themeBlock,
  WCAG_AA_NORMAL_TEXT,
} from './helpers/contrast';
import { themeRgb } from './helpers/palette';
import { FRONTEND_ROOT, shippedSources } from './helpers/sources';

/**
 * #642. `button.tsx` puts `disabled:opacity-50` in the shared base string. CSS
 * `opacity` groups the element, so the fill and the label are **each** blended
 * 50% with the page behind the button rather than composited against each other.
 *
 * For a button that is simply unavailable that is correct and deliberate — WCAG
 * 1.4.3 exempts text in an inactive component, and the greyed look is the
 * affordance. This codebase also uses `disabled` for **busy**: a button that
 * disables itself while its action runs and renders its own status text
 * ("Saving...", "Generating...", "Deleting..."). That text is the only feedback
 * the action is running, and the default variant's label drops from 6.29:1 to
 * **2.29:1** in light — the hardest text on the screen to read, at the moment it
 * matters most.
 *
 * `<Button busy>` (#642) restores full opacity, marks the state with
 * `aria-busy`, and leaves the unavailable state untouched everywhere.
 *
 * This guard has two halves, and the second is the one that keeps working:
 *
 *  1. the busy label clears 4.5:1 for each variant that can, measured from
 *     `tailwind.config.js` and `globals.css` rather than asserted;
 *  2. **every** `<Button>` whose label changes to a busy string while it
 *     disables itself carries `busy`. A fix that lands without a sweep is the
 *     #620/#635 shape three times over, so the sweep is the guard.
 */

const BUTTON = join(FRONTEND_ROOT, 'src', 'components', 'ui', 'button.tsx');
const GLOBALS = join(FRONTEND_ROOT, 'src', 'app', 'globals.css');

const WHITE: [number, number, number] = [255, 255, 255];

/** `rgb(r, g, b)` for a theme-fixed brand colour. */
const brandRgb = themeRgb;

/** The `disabled:opacity-*` the base string applies to an ordinary button. */
function baseDisabledOpacity(): number {
  const source = readFileSync(BUTTON, 'utf8');
  const match = source.match(/disabled:opacity-(\d+)\b(?![^"]*BUSY)/);
  if (!match) throw new Error('No `disabled:opacity-N` in button.tsx');
  return Number(match[1]) / 100;
}

/** The classes `busy` adds, read out of the component rather than restated. */
function busyClasses(): string {
  const source = readFileSync(BUTTON, 'utf8');
  const match = source.match(/const BUSY_CLASSES\s*=\s*"([^"]*)"/);
  if (!match) throw new Error('No `BUSY_CLASSES` in button.tsx');
  return match[1];
}

describe('busy buttons keep their status text legible (#642)', () => {
  it('reads the real values out of the component and the theme', () => {
    // Vacuity guard: every assertion below is derived from these, so a parse
    // that silently returns nothing would make the whole file pass.
    expect(baseDisabledOpacity()).toBeGreaterThan(0);
    expect(baseDisabledOpacity()).toBeLessThan(1);
    expect(brandRgb('primary')).toHaveLength(3);
    expect(busyClasses()).toContain('disabled:opacity-100');
    expect(busyClasses()).toContain('disabled:pointer-events-none');
  });

  it('reproduces the defect at the base opacity, so the fix is measured against it', () => {
    // If this stops failing AA, the premise of #642 has changed and the rest of
    // this file is measuring something else.
    const css = readFileSync(GLOBALS, 'utf8');
    const alpha = baseDisabledOpacity();
    const fill = brandRgb('primary');

    for (const theme of ['light', 'dark'] as const) {
      const block = themeBlock(css, theme);
      for (const surfaceName of ['background', 'card'] as const) {
        const surface = oklchToken(block, surfaceName);
        const ratio = contrastRatio(
          compositeOver(WHITE, alpha, surface),
          compositeOver(fill, alpha, surface)
        );
        expect(ratio).toBeLessThan(WCAG_AA_NORMAL_TEXT);
      }
    }
  });

  it('clears AA for the default variant in both themes, on both surfaces', () => {
    // `busy` restores opacity-100, so the label composites against its own fill
    // and the surface behind it no longer enters the maths. `bg-primary` and
    // `text-primary-foreground` are theme-fixed in `@theme` (#634), so
    // one ratio covers both themes — asserted per surface anyway, because the
    // day that stops being true is the day this should fail.
    const css = readFileSync(GLOBALS, 'utf8');
    const ratio = contrastRatio(WHITE, brandRgb('primary'));

    for (const theme of ['light', 'dark'] as const) {
      const block = themeBlock(css, theme);
      for (const surfaceName of ['background', 'card'] as const) {
        oklchToken(block, surfaceName); // the surface must exist to be irrelevant
        expect(ratio).toBeGreaterThanOrEqual(WCAG_AA_NORMAL_TEXT);
      }
    }
  });

  it('clears AA for the destructive variant too, in both themes', () => {
    // This recorded a shortfall until #682. `busy` took the two delete buttons
    // from 1.97:1 to 3.76:1 and no further, because the remainder was the brand
    // red itself — white on rgb(239, 68, 68) is below AA in *every* state,
    // enabled included. #682 moved the token to red-700, and this assertion
    // flipped from "record the gap" to "there is no gap", which is what the
    // recorded expectation was there to prompt.
    //
    // The fill is theme-fixed, so one ratio covers both themes; `text-destructive`
    // needs a dark override and is guarded in `destructive-text-contrast.test.ts`.
    const ratio = contrastRatio(WHITE, brandRgb('destructive-surface'));
    expect(ratio).toBeGreaterThanOrEqual(WCAG_AA_NORMAL_TEXT);
  });
});

/** `<Button ...>` or raw `<button ...>` spans, with JSX braces balanced so `{a > b}` cannot end a tag. */
function buttonElements(source: string, name: 'Button' | 'button' = 'Button'): { tag: string; body: string }[] {
  const found: { tag: string; body: string }[] = [];
  for (const match of source.matchAll(new RegExp(`<${name}\\b`, 'g'))) {
    const start = match.index!;
    let i = start + 1;
    let depth = 0;
    let tagEnd = -1;
    while (i < source.length) {
      const c = source[i];
      if (c === '{') depth++;
      else if (c === '}') depth--;
      else if (c === '>' && depth === 0) {
        tagEnd = i + 1;
        break;
      }
      i++;
    }
    if (tagEnd === -1) continue;
    const close = source.indexOf(`</${name}>`, tagEnd);
    found.push({ tag: source.slice(start, tagEnd), body: close === -1 ? '' : source.slice(tagEnd, close) });
  }
  return found;
}

/**
 * Any progress label, rather than a list of the ones that happened to exist.
 *
 * The first cut enumerated ten verbs, taken from what the sweep had already
 * found — which is circular, and the pre-PR reviewer produced four it missed:
 * `Verifying…` in `verify-2fa` and `TwoFactorSetup`, `Changing…` in
 * `PasswordChangeForm`, and `Please wait…` in `TwoFactorSetup`. A gerund plus an
 * ellipsis is the actual shape; `Please wait` is the one common label that is
 * not one.
 */
const BUSY_LABEL = /(\b\w+ing|Please wait)(\.\.\.|…)/;

describe('every busy-labelled Button declares it (#642)', () => {
  const sources = shippedSources().filter((path) => path.endsWith('.tsx'));

  it('sweeps the shipped components', () => {
    expect(sources.length).toBeGreaterThan(50);
    const buttons = sources.flatMap((path) => buttonElements(readFileSync(join(FRONTEND_ROOT, path), 'utf8')));
    expect(buttons.length).toBeGreaterThan(40);
  });

  it('recognises a busy button and clears an ordinary one', () => {
    // Anti-vacuity: pins the parser and the label pattern to fixtures, so a typo
    // in either cannot quietly green the sweep below.
    const busy = buttonElements(
      '<Button disabled={isSaving}>\n{isSaving ? "Saving..." : "Save"}\n</Button>'
    );
    expect(busy).toHaveLength(1);
    expect(BUSY_LABEL.test(busy[0].body)).toBe(true);
    expect(busy[0].tag).not.toContain('busy');

    // A `>` inside a JSX expression must not end the opening tag.
    const withComparison = buttonElements('<Button disabled={count > 0}>Save</Button>');
    expect(withComparison[0].tag).toBe('<Button disabled={count > 0}>');
    expect(BUSY_LABEL.test(withComparison[0].body)).toBe(false);
  });

  it('still finds the busy buttons it is supposed to be checking', () => {
    // The sweep below only fails on a busy-labelled Button that lacks `busy`, so
    // **narrowing `BUSY_LABEL` cannot fail it** — it just checks less. That is
    // exactly how the first cut of this pattern shipped, enumerating ten verbs
    // taken from what it had already found and missing twelve more sites.
    //
    // This is the floor that makes a narrowed pattern fail: the count can rise
    // freely, and may only drop when a busy label genuinely leaves the tree.
    const busyButtons = sources.flatMap((path) =>
      buttonElements(readFileSync(join(FRONTEND_ROOT, path), 'utf8')).filter(({ body }) =>
        BUSY_LABEL.test(body)
      )
    );

    expect(busyButtons.length).toBeGreaterThanOrEqual(23);
  });

  it('no shipped Button shows a busy label without `busy`', () => {
    const offenders = sources.flatMap((path) =>
      buttonElements(readFileSync(join(FRONTEND_ROOT, path), 'utf8'))
        .filter(({ tag, body }) => BUSY_LABEL.test(body) && !/\bbusy\b/.test(tag))
        .map(({ body }) => `${path} :: ${BUSY_LABEL.exec(body)![0]}`)
    );

    expect(offenders).toEqual([]);
  });
});

/**
 * Raw `<button>` elements with a busy label (#684).
 *
 * `buttonVariants` never styled these, so they neither had #642's defect nor got
 * its fix — they carry their own colours, and four of the six measured between
 * 2.29:1 and 4.09:1. Fixed in #684 by removing the opacity/pale-text treatment
 * from the states that are *only* ever busy, and making it conditional on the
 * two buttons that are disabled for two different reasons.
 *
 * `aria-busy` is the marker here rather than a colour assertion: these buttons
 * have no shared class string to read a ratio out of, and requiring the marker
 * forces a new hand-styled busy button through the same thinking rather than
 * letting it appear unmeasured.
 */
const RAW_BUSY_EXEMPT: ReadonlyArray<readonly [string, string]> = [
  [
    'src/app/dashboard/books/[bookId]/summary/page.tsx',
    // A microphone toggle, not a pending operation: `aria-pressed` already
    // conveys the state, and `aria-busy` ("this element is being updated") would
    // be the wrong word for it. Measured at 4.83:1 (white on red-600) with no
    // opacity treatment at all, so there is nothing to fix.
    'Listening',
  ],
];

describe('raw <button> elements with a busy label declare it (#684)', () => {
  const sources = shippedSources().filter((path) => path.endsWith('.tsx'));

  it('still finds the raw busy buttons', () => {
    const raw = sources.flatMap((path) =>
      buttonElements(readFileSync(join(FRONTEND_ROOT, path), 'utf8'), 'button').filter(({ body }) =>
        BUSY_LABEL.test(body)
      )
    );
    // Same floor logic as the `<Button>` sweep: narrowing the pattern must fail
    // rather than quietly check less.
    expect(raw.length).toBeGreaterThanOrEqual(6);
  });

  it('every raw busy button sets aria-busy, or is exempt with a reason', () => {
    const offenders = sources.flatMap((path) =>
      buttonElements(readFileSync(join(FRONTEND_ROOT, path), 'utf8'), 'button')
        .filter(({ tag, body }) => {
          if (!BUSY_LABEL.test(body)) return false;
          if (/aria-busy/.test(tag)) return false;
          const label = BUSY_LABEL.exec(body)![1];
          return !RAW_BUSY_EXEMPT.some(([file, exempt]) => path === file && exempt === label);
        })
        .map(({ body }) => `${path} :: ${BUSY_LABEL.exec(body)![0]}`)
    );

    expect(offenders).toEqual([]);
  });
});
