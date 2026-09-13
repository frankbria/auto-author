#!/usr/bin/env node
/**
 * Every Playwright spec must be reachable by some config (#613).
 *
 * `playwright.config.ts` sets `testDir: './src/e2e'` and the staging config
 * covers `tests/e2e/staging`. Nothing covers `tests/e2e/deployment` — so its 7
 * spec files have not executed since the testDir was narrowed on 2025-06-02,
 * fifteen months. They were edited as recently as 2026-07-13 (#289) by someone
 * who reasonably assumed they ran.
 *
 * That is worse than a failing test: a spec that never runs is indistinguishable
 * from a passing one in every report, and #613 found its page object had been
 * pointing at `data-testid`s the app has never rendered the whole time. The same
 * shape as the repo's "No unscanned npm lockfiles" step — a file in a place no
 * gate looks at.
 *
 * Ledgered rather than deleted: whether those specs should be wired up or
 * removed is a test-coverage decision, and this makes it explicit and countable
 * instead of silent. The ledger only shrinks.
 */
import { readdirSync, readFileSync, existsSync } from 'node:fs';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const LEDGER = join(ROOT, 'unrun-spec-baseline.json');

/** Every `testDir` any playwright config in the tree declares. */
function configuredDirs() {
  const configs = [];
  const walk = (dir) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      if (e.name === 'node_modules' || e.name === '.next') continue;
      const p = join(dir, e.name);
      if (e.isDirectory()) walk(p);
      else if (/^playwright\..*config\.(ts|js|mjs)$/.test(e.name)) configs.push(p);
    }
  };
  walk(ROOT);

  const dirs = [];
  for (const cfg of configs) {
    const m = /testDir:\s*['"`]([^'"`]+)['"`]/.exec(readFileSync(cfg, 'utf8'));
    if (!m) continue;
    dirs.push({ config: relative(ROOT, cfg), dir: resolve(dirname(cfg), m[1]) });
  }
  return dirs;
}

function specFiles(dir = ROOT) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    if (e.name === 'node_modules' || e.name === '.next' || e.name === 'test-results') return [];
    const p = join(dir, e.name);
    if (e.isDirectory()) return specFiles(p);
    return /\.spec\.[jt]sx?$/.test(e.name) ? [p] : [];
  });
}

const dirs = configuredDirs();
if (!dirs.length) {
  console.error('FAIL — no playwright config declares a testDir. This gate cannot be vacuous.');
  process.exit(1);
}

const specs = specFiles();
// Vacuity guard: if the walk stops finding specs, this passes forever.
if (specs.length < 15) {
  console.error(`FAIL — found only ${specs.length} spec files; the walk is probably broken.`);
  process.exit(1);
}

const covered = (file) => dirs.some(({ dir }) => !relative(dir, file).startsWith('..'));
const orphans = specs
  .filter((f) => !covered(f))
  .map((f) => relative(ROOT, f).split(sep).join('/'))
  .sort();

const ledger = existsSync(LEDGER) ? JSON.parse(readFileSync(LEDGER, 'utf8')).files : {};

// Reported, never failed: a config nothing invokes still *can* be run by hand,
// which is legitimate for the deployment smoke suite (it targets a live URL).
// Worth surfacing, because "has a config" and "is ever executed" are different
// facts and #613 conflated them.
const pkg = JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf8'));
const scripts = Object.values(pkg.scripts ?? {}).join('\n');

console.log('Playwright testDirs:');
for (const { config, dir } of dirs) {
  const invoked = config === 'playwright.config.ts' || scripts.includes(config);
  console.log(`  ${config} -> ${relative(ROOT, dir)}${invoked ? '' : '   (no npm script invokes this config)'}`);
}
console.log(`\n${specs.length} spec files, ${orphans.length} reachable by no config.\n`);

const unledgered = orphans.filter((f) => !(f in ledger));
const resolved = Object.keys(ledger).filter((f) => !orphans.includes(f));

if (resolved.length) {
  console.log('Now covered (or deleted) — remove these rows:');
  for (const f of resolved) console.log(`  ${f}`);
  console.log();
}

if (!unledgered.length) {
  console.log(`PASS — every spec is reachable, or ledgered (${orphans.length} known).`);
  process.exit(0);
}

console.log(`Spec files no config will ever run (${unledgered.length}):`);
for (const f of unledgered) console.log(`  ${f}`);
console.log(
  '\nFAIL — wire them into a config, delete them, or ledger each with a reason.\n' +
    'A spec that never runs reports identically to one that passes.'
);
process.exit(1);
