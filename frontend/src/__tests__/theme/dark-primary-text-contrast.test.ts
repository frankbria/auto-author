import { readFileSync } from 'fs';
import { join } from 'path';

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
 * The conversion below is validated against a real browser: it reproduces
 * axe-core's reported `#171717` background and `2.85` ratio from the issue.
 */

const GLOBALS_CSS = join(__dirname, '..', '..', 'app', 'globals.css');

/** oklch() → sRGB 0-255, via Oklab and the linear-sRGB matrix (D65). */
function oklchToRgb(L: number, C: number, hDeg: number): [number, number, number] {
  const h = (hDeg * Math.PI) / 180;
  const a = C * Math.cos(h);
  const b = C * Math.sin(h);

  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;

  const linear = [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ];

  return linear.map((c) => {
    const encoded = c <= 0.0031308 ? 12.92 * c : 1.055 * Math.max(c, 0) ** (1 / 2.4) - 0.055;
    return Math.round(Math.min(1, Math.max(0, encoded)) * 255);
  }) as [number, number, number];
}

function relativeLuminance([r, g, b]: [number, number, number]): number {
  const [lr, lg, lb] = [r, g, b].map((v) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * lr + 0.7152 * lg + 0.0722 * lb;
}

function contrastRatio(
  fg: [number, number, number],
  bg: [number, number, number]
): number {
  const [lighter, darker] = [relativeLuminance(fg), relativeLuminance(bg)].sort(
    (a, b) => b - a
  );
  return (lighter + 0.05) / (darker + 0.05);
}

/** The `.dark { ... }` block of globals.css. */
function darkBlock(css: string): string {
  const match = css.match(/^\.dark\s*\{([^}]*)\}/m);
  if (!match) throw new Error('No `.dark { ... }` block found in globals.css');
  return match[1];
}

/** Reads `--<name>: oklch(L C H)` out of a CSS block. */
function oklchToken(block: string, name: string): [number, number, number] {
  const match = block.match(
    new RegExp(`--${name}:\\s*oklch\\(([\\d.]+)\\s+([\\d.]+)\\s+([\\d.]+)\\)`)
  );
  if (!match) throw new Error(`No oklch \`--${name}\` in the .dark block`);
  return oklchToRgb(Number(match[1]), Number(match[2]), Number(match[3]));
}

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

const WCAG_AA_NORMAL_TEXT = 4.5;

describe('text-primary clears WCAG 2.1 AA on the dark surfaces (#610)', () => {
  const css = readFileSync(GLOBALS_CSS, 'utf8');

  it.each(DARK_SURFACES)('is at least 4.5:1 on --%s', (token) => {
    const ratio = contrastRatio(darkPrimaryTextColor(css), oklchToken(darkBlock(css), token));

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
