import { readFileSync } from 'fs';
import { join } from 'path';

import { FRONTEND_ROOT } from './sources';

/**
 * The palette the app actually renders, in `tailwindcss/colors`' shape (#513).
 *
 * Under Tailwind v4, `tailwindcss/colors` exports the oklch palette, which is a
 * different set of colours from v3's. globals.css pins v3's hex values in
 * `@theme`, so that pin, not the package export, is what every `text-red-600`
 * paints and what every published ratio was measured against.
 */
function readPalette(): Record<string, Record<string, string>> {
  const css = readFileSync(join(FRONTEND_ROOT, 'src', 'app', 'globals.css'), 'utf8');
  const palette: Record<string, Record<string, string>> = {};
  let count = 0;
  for (const [, hue, shade, hex] of css.matchAll(/--color-([a-z]+)-(\d{2,3}):\s*(#[0-9a-f]{6});/g)) {
    (palette[hue] ??= {})[shade] = hex;
    count++;
  }
  // Vacuity guard: a reformatted pin would otherwise hand every guard an empty
  // palette, and "unpriceable colour" paths can read as a pass.
  if (count < 200) throw new Error(`Only ${count} pinned palette colours found in globals.css`);
  return palette;
}

export const colors = readPalette();

/**
 * The raw `@theme` value behind a colour utility: `themeColor('primary')` is
 * what `bg-primary` paints, e.g. `rgb(79 70 229)` or `var(--muted)`. This is
 * what tailwind.config.js's `colors` held under v3. `undefined` if the theme
 * doesn't define the name.
 */
export function themeColor(name: string): string | undefined {
  const css = readFileSync(join(FRONTEND_ROOT, 'src', 'app', 'globals.css'), 'utf8');
  return css.match(new RegExp(`--color-${name}:\\s*([^;]+);`))?.[1].trim();
}

/** A theme colour that must be a literal `rgb(...)`, as channels. */
export function themeRgb(name: string): [number, number, number] {
  const value = themeColor(name);
  const rgb = value?.match(/^rgb\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)\s*\)$/);
  if (!rgb) throw new Error(`\`--color-${name}\` in globals.css is not an rgb() literal: ${value}`);
  return [Number(rgb[1]), Number(rgb[2]), Number(rgb[3])];
}
