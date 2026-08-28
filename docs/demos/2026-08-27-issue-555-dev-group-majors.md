# #555 — `frontend-dev` group majors: demo

Every acceptance criterion, with the outcome that proves it. All measurements are
`npm install --package-lock-only` in a scratch directory seeded from
`frontend/package-lock.json` at `main` (3d3bd98), against manifests reconstructed
from PR #548 (head `a0e6ab7`).

---

## Setup: what #548 actually contains

`gh pr view 548` says "14 updates". Comparing its manifest against `main`:

| kind | count | packages |
|---|---|---|
| MAJOR | 8 | `@testing-library/jest-dom` 6→7, `@typescript-eslint/eslint-plugin` 6→8, `@typescript-eslint/parser` 6→8, `eslint` 8→10, `eslint-config-next` 15→16, `jest-axe` 10→11, `tailwindcss` 3→4, `typescript` 5→7 |
| minor/patch | 4 | `@axe-core/react`, `@playwright/test`, `@testing-library/user-event`, `autoprefixer` |
| lockfile-only | 2 | `@types/react`, `postcss` (range unchanged) |

The issue said "twelve of the fourteen updates are unobjectionable". Measured, it is
six — four range bumps plus two lockfile-only moves. The shape of the complaint holds;
the number did not, and the config comment now carries the measured one.

## Baseline: the PR as it stands cannot install

```
$ npm install --package-lock-only        # #548's manifest, unmodified
npm error code ERESOLVE
npm error Found: typescript@7.0.2
npm error Could not resolve dependency:
npm error peer typescript@">=4.8.4 <6.1.0" from @typescript-eslint/parser@8.68.0
EXIT=1
```

Note the peer that fires: **`@typescript-eslint`, not `ts-jest`**. #514 recorded only
the `ts-jest` cap (`>=4.3 <7`); the `typescript-eslint` one is tighter and is the one
that actually stops the install. → **AC4**, added to #514 with this output.

---

## AC1 — tailwindcss no longer receives a major inside a grouped PR

`tailwindcss`, `postcss` and `autoprefixer` move to a `frontend-build` group restricted
to `minor`/`patch`, and are named in `frontend-dev`'s `exclude-patterns`. Their majors
match no group, so they arrive solo; their patches still batch.

Guard, run against `main`'s config (i.e. before the fix):

```
FAILED test_build_time_toolchains_never_ride_a_major_taking_group[/frontend:frontend-dev]
AssertionError: npm group 'frontend-dev' in /frontend takes majors and matches
'tailwindcss', which is dev-classified but emits an artifact every user downloads.
```

Against the new config: `40 passed, 4 skipped`.

Mutation-checked both ways — the guard is not vacuous:

| mutation | result |
|---|---|
| drop `exclude-patterns` from `frontend-dev` | 1 failed |
| drop `update-types` from `frontend-build` | 2 failed |

## AC2 — the wrong comment is gone

`# Dev deps never ship, so a major is a CI concern at worst.` is replaced. The new
comment states the actual rule — what a package *ships*, not which manifest section it
sits in — and names the three packages the classification gets wrong.

## AC3 — how a group behaves with a known-blocked major

Both named options, because each covers a different half.

**Measured first, because the obvious answer is wrong.** The first cut on this branch
barred *every* group from grouping a major. Each now-solo major, installed alone:

| bump | alone |
|---|---|
| `@testing-library/jest-dom` 6→7 | OK |
| `jest-axe` 10→11 | OK |
| `@typescript-eslint/eslint-plugin` 6→8 | **FAIL** — peer `@typescript-eslint/parser@^8.68.0` |
| `eslint` 8→10 | **FAIL** — peer `eslint@"^7 \|\| ^8"` from `@typescript-eslint/parser@6.21.0` |
| `eslint-config-next` 15→16 | **FAIL** — peer `eslint@">=9.0.0"` |

Three of the five cannot install on their own: the eslint family is peer-coupled and
only moves together. Splitting every dev major out would have produced four
permanently-unmergeable solo PRs — #555's own complaint, relocated. So `frontend-dev`
keeps its majors, and only the shipping toolchain leaves.

For the blocked pair specifically, `ignore` entries on `typescript` and `tailwindcss`
semver-major, each naming the issue (#514, #513) whose closure removes it.

## AC5 — a regenerated `frontend-dev` PR installs cleanly

#548 reconstructed under the new config — excluded packages dropped to
`frontend-build`, ignored majors dropped:

```
frontend-dev group keeps 9 of 14 updates:
  minor @axe-core/react                     ^4.11.0  -> ^4.13.0
  minor @playwright/test                    ^1.57.0  -> ^1.62.1
  MAJOR @testing-library/jest-dom           ^6.1.5   -> ^7.0.1
  minor @testing-library/user-event         ^14.5.1  -> ^14.6.5
  MAJOR @typescript-eslint/eslint-plugin    ^6.13.2  -> ^8.67.0
  MAJOR @typescript-eslint/parser           ^6.13.2  -> ^8.67.0
  MAJOR eslint                              ^8.57.0  -> ^10.8.1
  MAJOR eslint-config-next                  ^15.5.6  -> ^16.3.1
  MAJOR jest-axe                            ^10.0.0  -> ^11.0.0

npm warn ERESOLVE overriding peer dependency   (x3)
EXIT=0
```

Resolved lockfile, verified package by package:

| package | resolved |
|---|---|
| `eslint` | 10.9.1 |
| `eslint-config-next` | 16.3.3 |
| `@typescript-eslint/parser` | 8.68.0 |
| `@typescript-eslint/eslint-plugin` | 8.68.0 |
| `@testing-library/jest-dom` | 7.0.1 |
| `jest-axe` | 11.0.0 |
| `tailwindcss` | 3.4.19 — held, as intended |
| `typescript` | 5.9.3 — held, as intended |

**Exit 0 against ERESOLVE today.** The whole eslint cluster crosses its major together,
which is the outcome the coupling requires.

### One thing this does not clear

The three `npm warn ERESOLVE overriding peer dependency` lines are *new* — the same
command on `main`'s unmodified manifest emits zero. They are warnings, npm resolves and
`npm ci` will install, but the eslint-family majors do put the existing `overrides`
block (`js-yaml`, `@babel/core`) in tension with a peer range. That belongs to whoever
reviews the regenerated #548, not to this config change; it is recorded here so it is
not discovered as a surprise.
