import { existsSync, readFileSync } from 'fs';
import { join } from 'path';

import colors from 'tailwindcss/colors';

import {
  contrastRatio,
  hexToRgb,
  oklchToken,
  themeBlock,
  WCAG_AA_NON_TEXT,
} from './helpers/contrast';
import { FRONTEND_ROOT, shippedSources } from './helpers/sources';

/**
 * #635, split out of #629. #629 fixed the `ChapterTab` loading spinner; the same
 * hand-rolled `animate-spin` ring pattern appears at thirteen more sites, and
 * the guard #629 left behind — `status-dot-contrast.test.ts` — reads named
 * consts out of two chapter components, so it could never reach any of them.
 * That is the #620 shape a third time: the fix landed, the sweep did not follow.
 *
 * A spinner ring is the whole indicator — the label beside it is separate text —
 * so the ring colour is a non-text UI component under WCAG 2.1 **1.4.11**, floor
 * 3:1. `axe-core` does not evaluate non-text elements at all, so a clean axe run
 * says nothing here.
 *
 * ## What the sweep found that the issue did not
 *
 * | site | ring | surface | worst |
 * |---|---|---|---|
 * | `BookMetadataForm` | `gray-400` | `--background` | 2.54 |
 * | `ClarifyingQuestions` | `blue-400` | `--muted` | 2.33 |
 * | `TocReview` (regenerate) | `white` | `disabled:bg-muted` | **1.09** |
 * | `ChapterEditor` | `border-primary` | `--card` | **2.85** dark |
 * | `ui/loading-spinner` | `gray-300` | — | **1.35** |
 *
 * The issue listed the first two. It guessed the `border-white`-in-button cases
 * were "likely fine": two are (7.13 on `bg-green-800`), but the regenerate
 * button paints `disabled:bg-muted` at exactly the moment its spinner shows, so
 * that ring is white on `#f5f5f5`. And it missed `border-primary` entirely —
 * which is the #634 trap: `tailwind.config.js` pins `primary` to the brand
 * indigo `rgb(79, 70, 229)` and #610's override is `.dark .text-primary` only,
 * so `border-primary` does not flip with the theme.
 *
 * ## Surface-agnostic by default
 *
 * Rather than trace each spinner's parent — which goes stale the moment a
 * component is re-parented — every ring must clear 3:1 on **all three** surfaces
 * a spinner can land on, in its own theme. A ring that passes that is safe
 * wherever it is mounted. The two rings that legitimately cannot (white on a
 * green button) are ledgered in `spinner-baseline.json` with the surface named,
 * and the guard measures them against *that* surface rather than excusing them.
 */

const SRC = join(FRONTEND_ROOT, 'src');
const GLOBALS_CSS = join(SRC, 'app', 'globals.css');
const TAILWIND_CONFIG = join(FRONTEND_ROOT, 'tailwind.config.js');

const SURFACES = ['background', 'muted', 'card'] as const;
const THEMES = ['light', 'dark'] as const;

type Rgb = [number, number, number];
type Theme = (typeof THEMES)[number];

/**
 * A colour utility that can paint a spinner: the ring (`border-*`, any edge) or,
 * for the icon idiom, the glyph stroke (`text-*`). Width utilities like
 * `border-t-2` do not match — the name must start with a letter.
 */
const CLASS_BOUNDARY = String.raw`\s'"\`(),{}`;
const COLOUR_UTILITY = new RegExp(
  `(?:^|[${CLASS_BOUNDARY}])((?:[a-z0-9.\\[\\]-]+:)*)` +
    `((?:border(?:-[trblxyse])?|text|ring)-([a-z]+(?:-[a-z]+)*(?:-\\d{2,3})?))` +
    `(?=$|[${CLASS_BOUNDARY}])`,
  'g'
);

interface Utility {
  variants: string[];
  utility: string;
  name: string;
  property: string;
}

/**
 * `text-*` also spells the type scale, and `text-lg` on a spinner (sizing an SVG
 * by font-size is a common idiom) is not a colour. Left in, it made a site count
 * as coloured — so it needed no `inherits` row — while resolving to nothing.
 */
const TYPE_SCALE = new Set([
  'xs', 'sm', 'base', 'lg', 'xl', '2xl', '3xl', '4xl', '5xl', '6xl', '7xl', '8xl', '9xl',
  'left', 'center', 'right', 'justify', 'start', 'end',
  'ellipsis', 'clip', 'wrap', 'nowrap', 'balance', 'pretty',
]);

/** Colour utilities in one class expression. */
function colourUtilities(expression: string): Utility[] {
  return [...expression.matchAll(COLOUR_UTILITY)]
    .filter(([, , utility, name]) => !(utility.startsWith('text-') && TYPE_SCALE.has(name)))
    .map(([, variants, utility, name]) => ({
      variants: variants ? variants.split(':').filter(Boolean) : [],
      utility,
      name,
      // The edge suffix stays part of the property: `border-t` and `border-l`
      // set different things and must not cover each other.
      property: utility.slice(0, utility.length - name.length - 1),
    }));
}

/** Applies in the resting state of `theme` — not on hover/focus/group. */
function appliesIn(utility: Utility, theme: Theme): boolean {
  return theme === 'dark'
    ? utility.variants.length === 0 ||
        (utility.variants.length === 1 && utility.variants[0] === 'dark')
    : utility.variants.length === 0;
}

/**
 * The utilities that can paint in `theme`, per CSS property.
 *
 * A resting-state `dark:` beats an unprefixed sibling — asserting both would
 * fail the very `text-blue-600 dark:text-blue-400` pair #629 established. But
 * two utilities with the *same* variants on the same property are alternatives,
 * not duplicates (`isDark ? 'border-blue-400' : 'border-blue-600'`), so both are
 * kept: collapsing them would leave one branch permanently unchecked.
 */
function effective(expression: string, theme: Theme): Utility[] {
  const applying = colourUtilities(expression).filter((utility) => appliesIn(utility, theme));
  const darkProperties = new Set(
    applying.filter((u) => u.variants.length).map((u) => u.property)
  );

  return applying.filter((u) => u.variants.length || !darkProperties.has(u.property));
}

/**
 * Every `className` value in `source` that carries `animate-spin`, as one
 * expression per element.
 *
 * Scanning `className=` to its balanced end rather than keeping whole lines
 * matters twice over: a Prettier-wrapped multi-line `cn(...)` would otherwise be
 * invisible (the colour sits on a different line from `animate-spin`), and two
 * elements sharing one source line would have their utilities pooled — so an
 * unrelated sibling's `border-red-600` could stand in for a spinner's failing
 * `border-white`. Both were live holes in this guard's first draft.
 */
export function classNameExpressions(source: string): string[] {
  const consts = new Map<string, string>();
  // Any quote style: a const written with double quotes or backticks was
  // silently unresolvable in the first draft, which would have blinded the
  // sweep to the one site #629 already fixed.
  for (const [, name, a, b, c] of source.matchAll(
    /^const ([A-Z][A-Z0-9_]*) = (?:'([^']*)'|"([^"]*)"|`([^`]*)`)/gm
  )) {
    consts.set(name, a ?? b ?? c);
  }

  const expressions: string[] = [];
  const marker = /className=/g;
  for (const match of source.matchAll(marker)) {
    const start = match.index! + match[0].length;
    const opener = source[start];
    let end = start;

    if (opener === '"' || opener === "'" || opener === '`') {
      end = source.indexOf(opener, start + 1);
      if (end === -1) continue;
      end += 1;
    } else if (opener === '{') {
      let depth = 0;
      let quote: string | null = null;
      for (end = start; end < source.length; end += 1) {
        const character = source[end];
        if (quote) {
          if (character === quote && source[end - 1] !== '\\') quote = null;
          continue;
        }
        if (character === '"' || character === "'" || character === '`') quote = character;
        else if (character === '{') depth += 1;
        else if (character === '}') {
          depth -= 1;
          if (depth === 0) {
            end += 1;
            break;
          }
        }
      }
    } else {
      continue;
    }

    const expression = source
      .slice(start, end)
      // Quoted, so substituted classes keep the boundaries the extractor looks
      // for; an unquoted splice puts `)` straight after the last utility.
      .replace(/\b[A-Z][A-Z0-9_]*\b/g, (identifier) => {
        const value = consts.get(identifier);
        return value === undefined ? identifier : `'${value}'`;
      });

    if (expression.includes('animate-spin')) expressions.push(expression);
  }

  return expressions;
}
interface BaselineEntry {
  /** The Tailwind colour the ring is actually painted on at the moment it shows. */
  surface: string;
  /** How many rings with this utility the file may still contain, on that surface. */
  count: number;
  reason: string;
}

/**
 * A spinner painted in `currentColor` — inherited from an ancestor rather than
 * set on the element. The row names the utility it inherits and the surface it
 * lands on, and the guard measures that pair: an inheriting site is covered, not
 * excused. Without these rows such a site contributes no utility at all and is
 * simply absent from the sweep, which is how `ChapterEditor`'s save spinner sat
 * unmeasured in this guard's first draft.
 */
interface InheritEntry {
  inherits: string;
  surface: string;
  /**
   * How many colourless spinners the file may hold on this pair. Asserted for
   * *equality*, not as a ceiling: a row is per file, so a second colourless
   * spinner on a different pair — a `variant="destructive"` button added to a
   * file already ledgered for `text-foreground`/`background` — would otherwise
   * need no row and never be measured. That is the file-level trap the `sites`
   * ledger rejects two tests below, and it applies here too.
   */
  count: number;
  reason: string;
}

const ledger = JSON.parse(readFileSync(join(FRONTEND_ROOT, 'spinner-baseline.json'), 'utf8'));
const baseline: Record<string, BaselineEntry> = ledger.sites;
const inheriting: Record<string, InheritEntry> = ledger.inherits;

const css = readFileSync(GLOBALS_CSS, 'utf8');
const sources = shippedSources();

/**
 * Colours that carry no contrast obligation of their own. `currentColor` and
 * friends inherit; an inheriting spinner is covered by an `inherits` row below.
 */
const NOT_A_COLOUR = new Set(['transparent', 'current', 'inherit', 'none']);

/**
 * `tailwind.config.js` as the app loads it. Requiring the module rather than
 * regexing its text is the difference between reading
 * `theme.extend.colors.primary` and reading whatever `primary:` appears first —
 * a nested `sidebar: { primary: {...} }` group, which the shadcn template this
 * repo standardises on does add, would otherwise win.
 */
// eslint-disable-next-line @typescript-eslint/no-var-requires
const tailwindConfig = require(TAILWIND_CONFIG);
const BRAND_COLOURS: Record<string, unknown> =
  ((tailwindConfig.default ?? tailwindConfig).theme?.extend?.colors ?? {}) as Record<string, unknown>;

/**
 * Resolve a Tailwind colour name the way the running app does, in order:
 * `tailwind.config.js`'s `theme.extend.colors` (where the brand colours are
 * pinned — they outrank a `:root` custom property, the #634 lesson), then the
 * palette, then a `globals.css` token.
 */
function resolveColour(name: string, theme: Theme, property: string = 'text'): Rgb | null {
  if (NOT_A_COLOUR.has(name)) return null;
  if (name === 'white') return [255, 255, 255];
  if (name === 'black') return [0, 0, 0];

  // #610 overrode `.dark .text-primary` and nothing else, so in dark theme
  // `text-primary` is indigo-400 while `border-primary` is still brand indigo.
  // Resolving them the same way is what made #634's guard measure a colour that
  // never renders — and here it would falsely fail the export modal.
  if (name === 'primary' && theme === 'dark' && property === 'text') {
    const override = css.match(
      /\.dark\s+\.text-primary(?![\w-])[^{]*\{[^}]*color:\s*rgb\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)/
    );
    if (!override) throw new Error('globals.css has no `.dark .text-primary` rgb() override (#610)');
    return [Number(override[1]), Number(override[2]), Number(override[3])];
  }

  // `text-primary-foreground` comes from `colors.primary.foreground`, not from a
  // top-level `primary-foreground` key — and the config's literal there ("white")
  // beats the `--primary-foreground` token of the same name.
  const [group, ...rest] = name.split('-');
  const subkey = rest.join('-');
  const brand = BRAND_COLOURS[name] ?? (subkey ? BRAND_COLOURS[group] : undefined);
  if (brand && typeof brand === 'object') {
    const record = brand as Record<string, unknown>;
    const raw = BRAND_COLOURS[name] ? record.DEFAULT : record[subkey];
    if (raw === 'white') return [255, 255, 255];
    if (raw === 'black') return [0, 0, 0];
    const value = raw;
    const rgb = typeof value === 'string' ? value.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/) : null;
    if (rgb) return [Number(rgb[1]), Number(rgb[2]), Number(rgb[3])];
    // A `var(--token)` brand entry falls through to the token lookup below.
  }

  const palette = name.match(/^([a-z]+)-(\d{2,3})$/);
  if (palette) {
    const scale = (colors as unknown as Record<string, unknown>)[palette[1]];
    const value =
      typeof scale === 'object' && scale ? (scale as Record<string, string>)[palette[2]] : undefined;
    return value ? hexToRgb(value) : null;
  }

  try {
    return oklchToken(themeBlock(css, theme), name);
  } catch {
    return null;
  }
}

/**
 * Does `path` actually paint `surface` behind its spinner?
 *
 * A ledgered `surface` is otherwise a hand-written claim no test checks, and the
 * regression it hides is this PR's own headline bug: change the accept button's
 * `disabled:bg-green-800` to `disabled:bg-muted` and `border-white` still occurs
 * once, the counts still match, and the ratio is still measured against the
 * *string* "green-800" — 7.13 green while the shipped ring drops to 1.09.
 *
 * Evidence is either the background class written in the file, or — for an icon
 * inside a `<Button>` — the variant's own background from `button.tsx`, since
 * that is where the pair is actually defined. `ghost` and `link` paint no
 * background, so their icons sit on the page surface.
 */
const BUTTON_VARIANTS = (() => {
  const source = readFileSync(join(SRC, 'components', 'ui', 'button.tsx'), 'utf8');
  // Scoped to the `variant:` group. `size:` has its own `default` key, and an
  // unscoped scan let it overwrite the colour one — so every default-variant
  // button resolved to `h-9 px-4 py-2` and looked like it painted no background.
  const from = source.indexOf('variant: {');
  const to = source.indexOf('size: {', from);
  if (from === -1 || to === -1) {
    throw new Error('button.tsx no longer has a `variant: {` … `size: {` shape — the ledger cannot be checked');
  }

  const variants = new Map<string, string>();
  for (const [, name, body] of source.slice(from, to).matchAll(/(\w+):\s*\n?\s*"([^"]+)"/g)) {
    variants.set(name, body);
  }
  if (!variants.has('default') || !variants.has('destructive')) {
    throw new Error('button.tsx variant definitions did not parse — the ledger cannot be checked');
  }
  return variants;
})();

/** Variants that paint nothing, so their contents sit on the page surface. */
const TRANSPARENT_VARIANTS = new Set(['ghost', 'link']);
const PAGE_SURFACES = new Set(['background', 'card', 'muted', 'popover']);

/**
 * Variants a background may carry and still be the surface behind the spinner.
 *
 * `disabled` counts because these buttons disable themselves *while loading* —
 * that is the state the spinner renders in. `hover`/`focus`/`active` do not: a
 * hover background is not what the ring sits on at rest, and accepting one is
 * how the first version of this check passed the mutation it exists to catch —
 * swapping `disabled:bg-green-800` for `disabled:bg-muted` left the sibling
 * `hover:bg-green-800` behind as false evidence.
 */
const RESTING_VARIANTS = new Set(['disabled', 'dark']);

/** Does `source` set `bg-<surface>` in a state the spinner is actually shown in? */
function paintsAtRest(source: string, surface: string): boolean {
  const pattern = new RegExp(
    `(?:^|[\\s'"\`])((?:[a-z0-9-]+:)*)bg-${surface}(?:/\\d+)?(?=$|[\\s'"\`])`,
    'gm'
  );
  return [...source.matchAll(pattern)].some(([, variants]) =>
    (variants ? variants.split(':').filter(Boolean) : []).every((v) => RESTING_VARIANTS.has(v))
  );
}

function paintsSurface(path: string, surface: string): boolean {
  const source = readFileSync(join(FRONTEND_ROOT, path), 'utf8');

  if (paintsAtRest(source, surface)) return true;
  // A CSS custom property pointing at the token (Sonner sets `--normal-bg`).
  if (source.includes(`var(--${surface})`)) return true;

  const used = [...source.matchAll(/variant="(\w+)"/g)].map(([, name]) => name);
  // A `<Button` with no variant prop takes `default`.
  if (/<Button[\s>]/.test(source)) used.push('default');

  return used.some((name) => {
    if (TRANSPARENT_VARIANTS.has(name)) return PAGE_SURFACES.has(surface);
    const body = BUTTON_VARIANTS.get(name);
    return body ? paintsAtRest(body, surface) : false;
  });
}

/** One `className` expression carrying `animate-spin`, in one file. */
interface Site {
  path: string;
  expression: string;
  utilities: Utility[];
}

const sites: Site[] = sources.flatMap((path) =>
  classNameExpressions(readFileSync(join(FRONTEND_ROOT, path), 'utf8')).map((expression) => ({
    path,
    expression,
    utilities: colourUtilities(expression),
  }))
);

/** Distinct colour utilities per file — counted per site, so a theme-only
 *  utility (`dark:border-blue-400` with no unprefixed sibling) still counts. */
const utilityCounts = new Map<string, number>();
for (const site of sites) {
  for (const utility of new Set(site.utilities.map((u) => u.utility))) {
    const key = `${site.path} :: ${utility}`;
    utilityCounts.set(key, (utilityCounts.get(key) ?? 0) + 1);
  }
}

describe('every animate-spin ring clears WCAG 2.1 1.4.11 (#635)', () => {
  it('extracts one expression per element, follows consts, ignores widths', () => {
    // Anti-vacuity: once the tree is clean the sweep passes whether or not the
    // extractor still works, so pin it to fixtures. Every case below was a live
    // hole in this guard's first draft, found by review.
    expect(
      colourUtilities('"animate-spin rounded-full h-3 w-3 border-t-2 border-b-2 border-gray-400 mr-2"').map(
        (u) => u.utility
      )
    ).toEqual(['border-gray-400']);

    // Width utilities are not colours; neither is a bare `border-2`.
    expect(colourUtilities('"border-t-2 border-b-2 border-2"')).toEqual([]);

    // Two elements on one source line stay separate — pooling them let an
    // unrelated sibling's colour stand in for the ring's.
    expect(
      classNameExpressions('<div className="animate-spin border-white" /><div className="border-red-600" />')
    ).toEqual(['"animate-spin border-white"']);

    // A Prettier-wrapped multi-line class list keeps its colour.
    expect(
      classNameExpressions(
        "<div className={cn(\n  'animate-spin rounded-full h-3 w-3',\n  'border-t-2 border-b-2 border-gray-400 mr-2'\n)} />"
      ).flatMap((e) => colourUtilities(e).map((u) => u.utility))
    ).toEqual(['border-gray-400']);

    // A same-file const is followed whatever quote style declares it.
    for (const quote of ["'", '"', '`']) {
      expect(
        classNameExpressions(
          `const SPIN = ${quote}text-blue-600 dark:text-blue-400${quote};\n<i className={cn('animate-spin', SPIN)} />`
        ).flatMap((e) => colourUtilities(e).map((u) => u.utility))
      ).toEqual(['text-blue-600', 'text-blue-400']);
    }

    // Only the resting-state `dark:` utility paints in dark...
    expect(effective('"animate-spin text-blue-600 dark:text-blue-400"', 'dark').map((u) => u.utility)).toEqual([
      'text-blue-400',
    ]);
    expect(effective('"animate-spin text-blue-600 dark:text-blue-400"', 'light').map((u) => u.utility)).toEqual([
      'text-blue-600',
    ]);
    // ...but two same-variant utilities on one property are a conditional's two
    // branches, not duplicates: collapsing them leaves one branch unchecked.
    expect(
      effective("{cn('animate-spin', isDark ? 'border-blue-400' : 'border-blue-600')}", 'light')
        .map((u) => u.utility)
        .sort()
    ).toEqual(['border-blue-400', 'border-blue-600']);
    // Different edges are different properties, not substitutes for each other.
    expect(effective('"border-gray-300 border-t-primary"', 'light').map((u) => u.utility).sort()).toEqual([
      'border-gray-300',
      'border-t-primary',
    ]);
  });

  it('resolves colours the way the app does', () => {
    // `border-primary` is the theme-fixed brand indigo in both themes...
    expect(resolveColour('primary', 'dark', 'border')).toEqual([79, 70, 229]);
    expect(resolveColour('primary', 'light', 'text')).toEqual([79, 70, 229]);
    // ...while `text-primary` in dark is #610's override, not the brand colour.
    expect(resolveColour('primary', 'dark', 'text')).toEqual([129, 140, 248]);
    // Read from the config object, so a nested same-named key cannot win.
    expect(BRAND_COLOURS.primary).toEqual({ DEFAULT: 'rgb(79, 70, 229)', foreground: 'white' });
  });

  it('sweeps the whole src tree, and never itself', () => {
    expect(sources.length).toBeGreaterThan(150);
    expect(sources).toContain('src/components/toc/TocReview.tsx');
    expect(sources).toContain('src/components/chapters/ChapterTab.tsx');
    expect(sources).not.toContain('src/__tests__/theme/spinner-ring-contrast.test.ts');

    // Vacuity: the tree really does contain a fleet of these.
    expect(sites.length).toBeGreaterThanOrEqual(20);
    expect(new Set(sites.map((s) => s.path)).size).toBeGreaterThanOrEqual(12);
  });

  it('leaves no spinner unaccounted for, in either theme', () => {
    // The claim in this file's title is "every" — so a site that resolves no
    // colour must be declared as inheriting one, not silently skipped.
    //
    // Per theme, not overall: a ring whose only colour utility is variant-
    // prefixed (`dark:border-blue-400`, or a `disabled:`-only one) produces no
    // light-theme case at all, yet `utilities` is non-empty — so an overall
    // check leaves it painting Preflight's default border colour, invisible,
    // with the guard green.
    const unaccounted = sites.flatMap((site) =>
      THEMES.filter((theme) => !effective(site.expression, theme).length)
        .filter(() => !(site.path in inheriting))
        .map((theme) => `${site.path} (${theme})`)
    );

    expect([...new Set(unaccounted)]).toEqual([]);
  });

  describe.each(THEMES)('%s theme', (theme) => {
    const cases = sites.flatMap((site) =>
      effective(site.expression, theme)
        .filter((utility) => !(`${site.path} :: ${utility.utility}` in baseline))
        .flatMap((utility) =>
          SURFACES.map((surface) => [site.path, utility.utility, surface, utility.name, utility.property] as const)
        )
    );

    it.each(cases)('%s `%s` clears 3:1 on --%s', (path, utility, surface, name, property) => {
      const colour = resolveColour(name, theme, property);
      // Loud, not silent: a name this resolver cannot price is #634's rule, and
      // dropping it here would let `border-[#e5e7eb]` — or a `text-lg` mistaken
      // for a colour — pass as though it were safe.
      if (colour === null && !NOT_A_COLOUR.has(name)) {
        throw new Error(`Unpriceable spinner colour \`${utility}\` in ${path}`);
      }
      if (colour === null) return; // `border-transparent` and friends

      expect(contrastRatio(colour, oklchToken(themeBlock(css, theme), surface))).toBeGreaterThanOrEqual(
        WCAG_AA_NON_TEXT
      );
    });

    it.each(Object.entries(inheriting))('%s inherits a colour that clears 3:1', (_path, entry) => {
      const name = entry.inherits.replace(/^(?:border(?:-[trblxyse])?|text|ring)-/, '');
      const property = entry.inherits.slice(0, entry.inherits.length - name.length - 1);
      const ring = resolveColour(name, theme, property);
      const surface = resolveColour(entry.surface, theme, 'bg');

      expect({ ring: ring !== null, surface: surface !== null }).toEqual({ ring: true, surface: true });
      expect(contrastRatio(ring!, surface!)).toBeGreaterThanOrEqual(WCAG_AA_NON_TEXT);
    });
  });

  it('measures every ledgered ring against the surface it names', () => {
    // The ledger is not an exemption list: a row states the surface the ring is
    // actually painted on, and the ratio is asserted against *that*.
    const failures = Object.entries(baseline).flatMap(([key, entry]) => {
      const utility = key.split(' :: ')[1];
      const name = utility.replace(/^(?:border(?:-[trblxyse])?|text|ring)-/, '');
      const property = utility.slice(0, utility.length - name.length - 1);

      return THEMES.flatMap((theme) => {
        const ring = resolveColour(name, theme, property);
        const surface = resolveColour(entry.surface, theme, 'bg');
        if (!ring || !surface) return [`${key}: unresolvable (${entry.surface})`];
        const ratio = contrastRatio(ring, surface);
        return ratio >= WCAG_AA_NON_TEXT ? [] : [`${key} on ${entry.surface} (${theme}): ${ratio.toFixed(2)}`];
      });
    });

    expect(failures).toEqual([]);
  });

  it('ledgers a surface the file actually paints', () => {
    const unsupported = [
      ...Object.entries(baseline).map(([key, entry]) => [key.split(' :: ')[0], key, entry.surface] as const),
      ...Object.entries(inheriting).map(([path, entry]) => [path, path, entry.surface] as const),
    ]
      .filter(([path, , surface]) => !paintsSurface(path, surface))
      .map(([, key, surface]) => `${key}: nothing in the file paints \`${surface}\``);

    expect(unsupported).toEqual([]);
  });

  it('ledgers only what still exists, each with a surface, a count and a reason', () => {
    // Counted per value, not per file: `TocReview` shipped *two* `border-white`
    // rings on two different surfaces, and a file-level row would have
    // pre-authorised the 1.09:1 one along with the 7.13:1 one.
    const stale = Object.keys(baseline).filter((key) => !utilityCounts.has(key));
    expect(stale).toEqual([]);

    const overCount = Object.entries(baseline)
      .filter(([key, entry]) => (utilityCounts.get(key) ?? 0) > entry.count)
      .map(([key, entry]) => `${key}: ${utilityCounts.get(key)} > ${entry.count} ledgered`);
    expect(overCount).toEqual([]);

    const colourlessCounts = new Map<string, number>();
    for (const site of sites) {
      if (site.utilities.length) continue;
      colourlessCounts.set(site.path, (colourlessCounts.get(site.path) ?? 0) + 1);
    }

    const staleInherits = Object.keys(inheriting).filter((path) => !colourlessCounts.has(path));
    expect(staleInherits).toEqual([]);

    const miscounted = Object.entries(inheriting)
      .filter(([path, entry]) => (colourlessCounts.get(path) ?? 0) !== entry.count)
      .map(([path, entry]) => `${path}: ${colourlessCounts.get(path)} colourless spinners, ${entry.count} ledgered`);
    expect(miscounted).toEqual([]);

    const unexplained = [
      ...Object.entries(baseline)
        .filter(([, e]) => !e.reason?.trim() || !e.surface?.trim() || !(e.count > 0))
        .map(([key]) => key),
      ...Object.entries(inheriting)
        .filter(([, e]) => !e.reason?.trim() || !e.surface?.trim() || !e.inherits?.trim() || !(e.count > 0))
        .map(([key]) => key),
    ];
    expect(unexplained).toEqual([]);

    const missingFiles = [
      ...Object.keys(baseline).map((key) => key.split(' :: ')[0]),
      ...Object.keys(inheriting),
    ].filter((path) => !existsSync(join(FRONTEND_ROOT, path)));
    expect(missingFiles).toEqual([]);
  });

  it('reproduces the 2.33:1 figure #629 fixed, at the site the #629 guard could not reach', () => {
    const beforeFix = contrastRatio(hexToRgb(colors.blue[400]), oklchToken(themeBlock(css, 'light'), 'muted'));

    expect(beforeFix).toBeCloseTo(2.33, 1);
    expect(beforeFix).toBeLessThan(WCAG_AA_NON_TEXT);
  });

  it('reproduces the 1.09:1 white ring on the regenerate button (#635)', () => {
    // The issue guessed this one was "likely fine, unverified". The button sets
    // `disabled:bg-muted` and `disabled` is driven by the same `isLoading` flag
    // that shows the spinner, so `--muted` is what paints behind it.
    const beforeFix = contrastRatio([255, 255, 255], oklchToken(themeBlock(css, 'light'), 'muted'));

    expect(beforeFix).toBeCloseTo(1.09, 1);
    expect(beforeFix).toBeLessThan(WCAG_AA_NON_TEXT);
  });

  it('reproduces border-primary at 2.85:1 on dark --card (#635)', () => {
    // Not the `--primary` token, which would be 14.23 here: `tailwind.config.js`
    // pins `primary` to brand indigo and #610 overrode only `.dark .text-primary`.
    const brand = resolveColour('primary', 'dark', 'border')!;
    const beforeFix = contrastRatio(brand, oklchToken(themeBlock(css, 'dark'), 'card'));

    expect(beforeFix).toBeCloseTo(2.85, 1);
    expect(beforeFix).toBeLessThan(WCAG_AA_NON_TEXT);
  });
});
