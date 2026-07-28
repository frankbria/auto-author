# Demo — #342 Supply-chain automation mis-aimed

**Date:** 2026-07-27 · **Branch:** `feature/342-supply-chain-automation`

Every acceptance criterion below is demonstrated with **outcome** evidence — what
changed in the world — not "the config parses" or "the step exited 0".

---

## AC1 — Point Dependabot at `/frontend`

The claim to prove is not "the YAML changed" but "the target it watches went from
nothing to the real tree".

```
root package.json dependencies + devDependencies : 0
root package-lock.json exists                    : NO
frontend/package-lock.json packages              : 1122
```

Dependabot's npm ecosystem needs a manifest **and** a lockfile to resolve
updates. Aimed at `/` it had a zero-dependency `package.json` and no lockfile —
so it produced no PRs and no alerts, which is precisely why nothing ever fired.
Now aimed at `/frontend`, where 1122 packages live.

✅ **Outcome:** the monitored surface goes 0 → 1122 packages.

---

## AC2 — Committed `pip-audit` + `npm audit` CI step

The gate is `scripts/audit_gate.py` + `security-baseline.json`, wired as the
`security-audit` job. Three behaviours matter, each shown:

**(a) It passes on the current tree** — so `main` does not go red on day one:

```
$ python3 scripts/audit_gate.py --pip-audit pip.json --npm-audit npm.json \
    --baseline security-baseline.json
Scanned 91 advisories against security-baseline.json

PASS — no new advisories (91 known, already in the baseline).
EXIT=0
```

**(b) It fails on a NEW advisory** — the whole point. One entry removed from the
baseline to simulate an advisory appearing tomorrow:

```
New advisories not in the baseline (1):
  [npm] GHSA-22p9-wv53-3rq4  linkify-it  severity=high  fix=yes

FAIL — fix these, or add each ID to the baseline with a reason if it is accepted debt.
EXIT=1
```

**(c) It fails closed on an unrecognised advisory shape** — codex's review
scenario, a critical advisory carrying no GHSA URL, injected into the real audit
output:

```
New advisories not in the baseline (1):
  [npm] npm-source-123456  evil-pkg  severity=critical  fix=-
EXIT=1
```

Before the review fix this same input exited **0**.

✅ **Outcome:** a gate that is green today, red on anything new, and red rather
than silent on anything it doesn't understand.

### Why a baseline rather than a bare `npm audit --audit-level=high`

Measured on `main` before any change — the literal AC wording would have failed
immediately and been switched off within a week:

| Ecosystem | Result of a bare gate on `main` |
|---|---|
| `npm audit --audit-level=high` (frontend) | **fails** — 20 high, 2 critical (7 high + 1 critical even with `--omit=dev`) |
| `pip-audit` (backend prod deps) | **fails** — 64 advisories across 11 packages |

---

## AC3 — Remove `python-jose` and re-lock

Measured against a pristine `main` worktree, same tool, same command:

```
BEFORE (main):   64 advisories across 11 packages
AFTER  (branch): 49 advisories across  8 packages
ELIMINATED:      15 advisories; packages gone: cryptography, ecdsa, pyasn1
```

All three entered the tree **solely** as `python-jose` dependencies — including
`ecdsa`, carrying the Minerva timing CVE the issue named.

✅ **Outcome:** 15 real advisories eliminated, not deferred into the baseline.

---

## AC4 — Remove `passlib` via the ordered removal

The issue's premise-check was right that a bare dep-drop would break the build:
`app/core/security.py:1` imported `passlib`, and six endpoint modules import that
file, so it loaded on **every request path**. Order followed: delete
`hash_password`/`verify_password`/`pwd_context` and the import → delete the 5
covering tests → *then* drop the dependency and re-lock.

```
import jose        : gone
import passlib     : gone
import ecdsa       : gone
import cryptography: gone
import pyasn1      : gone

backend suite: 1164 passed, 11 skipped — 92% coverage (floor is 85%)
frontend suite: 128 suites, 2240 passed
```

`uv sync` uninstalled 9 packages; the app imports and every test still passes.

**Second install path caught during docs sync:** `scripts/deploy.sh:32` and
`scripts/deploy-fixed.sh:91` deploy production with
`uv pip install -r requirements.txt`, not from `uv.lock`. Re-locking alone would
have left `python-jose`, `passlib` and `ecdsa` shipping to production. The same 9
packages were removed from `requirements.txt` and the two entries from
`requirements.in` — a set that matches exactly what `uv sync` uninstalled, which
cross-validates it. `uv pip install --dry-run -r requirements.txt` resolves clean
with none reappearing.

✅ **Outcome:** the libraries are absent from **both** install paths, and the
suite proves nothing depended on them.

---

## AC5 — Delete `frontend/scripts/`

The issue described a "stray untracked `frontend/scripts/package-lock.json`".
No such file exists, and both files there were tracked. The real finding is
worse: `system-test.js` authenticates with `Authorization: Bearer ${API_TOKEN}`,
but the backend replaced JWT/bearer auth with better-auth session cookies
(`app/core/better_auth_session.py` reads cookies only) — **it cannot succeed
against the current API**.

`SYSTEM_TESTS.md`, which documented it, was equally dead: it also pointed at
`SystemIntegration.test.tsx` and `SystemE2E.test.tsx` (neither file exists) and
an `npm run test:system` script that is not defined in `package.json`. All three
of its documented entry points were broken.

```
frontend/scripts exists                  : NO
'colors' declared anywhere in repo       : 0 files
```

✅ **Outcome:** the protestware `colors` declaration is gone from the repo, and
so is a document whose every instruction was broken.

---

## Review

Cross-family review by **codex** (opencode hung with zero output — the
documented failure mode — so the fallback was used, disclosed on the PR).

- **1 finding, adopted and fixed:** the false-green path in `parse_npm_audit`,
  fixed and mutation-verified above.
- codex empirically confirmed the workflow's `|| rc=$?` and
  `rc=${PIPESTATUS[0]}`-after-`tee` idioms preserve exit codes under `bash -e`
  (it ran them).
- No dangling references to the removed `passlib`/`python-jose` symbols.

---

## Known limitations

- **91 advisories remain as accepted debt** in `security-baseline.json`. This PR
  makes them explicit and blocks new ones; it does not fix them. Clearing them
  needs major bumps (pillow 11→12, starlette 0.47→1.3, next/postcss/sharp) and
  belongs in its own PR with a full regression pass.
- **The audit gate reads `uv.lock`, production deploys from `requirements.txt`.**
  Both are cleaned here, but they are separately maintained and have already
  drifted — `requirements.in` never gained `sentry-sdk` (#334). Worth a
  follow-up issue to make one generated from the other; deliberately not
  widened into this PR.
- `npm audit` in CI resolves from the lockfile against the live registry, so the
  job needs network. A registry outage surfaces as a non-0/1 exit and fails the
  job loudly rather than silently passing.
