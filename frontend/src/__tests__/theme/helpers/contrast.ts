/**
 * Shared colour maths for the theme contrast guards (#610, #618, #620).
 *
 * Extracted from `dark-primary-text-contrast.test.ts`, where the conversion was
 * validated against a real browser: it reproduces axe-core's reported `#171717`
 * background and `2.85` ratio from #610. jsdom carries no stylesheet and no
 * layout, so `jest-axe` cannot see any of this — recomputing from the values
 * actually in `globals.css` is the real guard.
 *
 * `getComputedStyle` in a browser returns `lab()`/`oklch()` for these tokens, not
 * `rgb()`, so hand-rolled ratios taken off the DOM are unreliable (see the repo's
 * `axe-contrast-verification-traps` note). This module works from the source
 * token values instead.
 */

/** oklch() → sRGB 0-255, via Oklab and the linear-sRGB matrix (D65). */
export function oklchToRgb(L: number, C: number, hDeg: number): [number, number, number] {
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

export function relativeLuminance([r, g, b]: [number, number, number]): number {
  const [lr, lg, lb] = [r, g, b].map((v) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * lr + 0.7152 * lg + 0.0722 * lb;
}

export function contrastRatio(
  fg: [number, number, number],
  bg: [number, number, number]
): number {
  const [lighter, darker] = [relativeLuminance(fg), relativeLuminance(bg)].sort(
    (a, b) => b - a
  );
  return (lighter + 0.05) / (darker + 0.05);
}

/** The `:root { ... }` (light) or `.dark { ... }` block of globals.css. */
export function themeBlock(css: string, theme: 'light' | 'dark'): string {
  const selector = theme === 'dark' ? '\\.dark' : ':root';
  const match = css.match(new RegExp(`^${selector}\\s*\\{([^}]*)\\}`, 'm'));
  if (!match) throw new Error(`No \`${theme === 'dark' ? '.dark' : ':root'} { ... }\` block in globals.css`);
  return match[1];
}

/** Reads `--<name>: oklch(L C H)` out of a CSS block. */
export function oklchToken(block: string, name: string): [number, number, number] {
  const match = block.match(
    new RegExp(`--${name}:\\s*oklch\\(([\\d.]+)\\s+([\\d.]+)\\s+([\\d.]+)\\)`)
  );
  if (!match) throw new Error(`No oklch \`--${name}\` in the block`);
  return oklchToRgb(Number(match[1]), Number(match[2]), Number(match[3]));
}

export const WCAG_AA_NORMAL_TEXT = 4.5;
