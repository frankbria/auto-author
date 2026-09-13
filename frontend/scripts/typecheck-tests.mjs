#!/usr/bin/env node
/**
 * Type-check the test sources (#625).
 *
 * `tsconfig.json` excludes `**\/*.test.ts(x)`, `**\/__tests__/**`, `jest.setup.ts`,
 * `**\/playwright*.ts` and `**\/e2e/**`, so `npm run typecheck` sees none of the
 * ~170 test files. Jest runs through `next/jest`, which transpiles with SWC and
 * strips types **without checking them**. Between the two, a test file can pass
 * the wrong argument type, reference a prop that no longer exists, or `await` a
 * non-promise, and every gate in the repo stays green.
 *
 * That matters most for the guards. `src/__tests__/theme/*` is the entire
 * enforcement for #331/#610/#618/#620/#623/#629/#632/#634/#637 — they parse CSS
 * and JSON by hand — and a type error in a guard is a guard that may not be
 * guarding. All eight are type-clean today, which is why none of them is in the
 * ledger: a type error introduced in one fails this gate immediately.
 *
 * Deleting the exclusions outright was not an option: 176 errors across 29 files
 * would have blocked the next PR touching any of them. So this is the ledgered
 * shape the repo already uses for `security-baseline.json` and
 * `gray-literal-baseline.json` — new test code is checked, the backlog is
 * explicit and countable, and it can only shrink.
 */
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const FRONTEND_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const BASELINE = resolve(FRONTEND_ROOT, 'typecheck-test-baseline.json');
const PROJECT = resolve(FRONTEND_ROOT, 'tsconfig.test.json');

/** `tsc` exits non-zero when it finds errors, which is the normal case here. */
function runTsc() {
  try {
    execFileSync('npx', ['tsc', '--noEmit', '-p', PROJECT], {
      cwd: FRONTEND_ROOT,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    return '';
  } catch (err) {
    // A crashed tsc and a tsc that found errors both land here. Distinguish
    // them: real diagnostics always match the `file(line,col): error TSxxxx`
    // shape, so output with none of those is a broken run, not a clean one.
    const out = `${err.stdout ?? ''}${err.stderr ?? ''}`;
    if (!out.trim()) {
      console.error('FAIL — tsc produced no output and exited non-zero.');
      process.exit(1);
    }
    return out;
  }
}

/** file → error count, from tsc's diagnostic lines. */
function countByFile(output) {
  const counts = {};
  for (const line of output.split('\n')) {
    const m = /^(\S+?)\(\d+,\d+\): error TS\d+:/.exec(line);
    if (m) counts[m[1]] = (counts[m[1]] ?? 0) + 1;
  }
  return counts;
}

const baseline = JSON.parse(readFileSync(BASELINE, 'utf8')).files;
const actual = countByFile(runTsc());

const unledgered = Object.entries(actual)
  .filter(([file]) => !(file in baseline))
  .map(([file, errors]) => ({ file, errors }));

const regressed = Object.entries(actual)
  .filter(([file]) => file in baseline)
  .map(([file, errors]) => ({ file, errors, ledgered: baseline[file].errors }))
  .filter(({ errors, ledgered }) => errors > ledgered);

// Reported, not failed — the same contract audit_gate.py uses. A row that has
// been burned down should be deleted, but nobody's build should break because
// someone fixed something.
const resolved = Object.keys(baseline).filter((file) => !(file in actual));
const shrunk = Object.entries(baseline)
  .filter(([file, entry]) => file in actual && actual[file] < entry.errors)
  .map(([file, entry]) => ({ file, was: entry.errors, now: actual[file] }));

const total = Object.values(actual).reduce((a, b) => a + b, 0);
console.log(`Type-checked the test sources: ${total} errors across ${Object.keys(actual).length} files.\n`);

if (resolved.length) {
  console.log('Now clean — delete these rows from typecheck-test-baseline.json:');
  for (const file of resolved.sort()) console.log(`  ${file}`);
  console.log();
}
if (shrunk.length) {
  console.log('Shrunk — lower these counts:');
  for (const { file, was, now } of shrunk) console.log(`  ${file}: ${was} -> ${now}`);
  console.log();
}

if (!unledgered.length && !regressed.length) {
  console.log(`PASS — no new type errors in test sources (${total} known, all ledgered).`);
  process.exit(0);
}

if (unledgered.length) {
  console.log(`Type errors in files with no ledger row (${unledgered.length}):`);
  for (const { file, errors } of unledgered) console.log(`  ${file}  (${errors})`);
  console.log();
}
if (regressed.length) {
  console.log(`Ledgered files above their recorded count (${regressed.length}):`);
  for (const { file, errors, ledgered } of regressed) {
    console.log(`  ${file}  ${ledgered} -> ${errors}`);
  }
  console.log();
}
console.log(
  'FAIL — fix these. Adding a ledger row to silence a NEW error defeats the gate;\n' +
    'the ledger records the backlog that existed when #625 turned this on, and only shrinks.'
);
process.exit(1);
