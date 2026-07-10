# Issue #192 [P1.12] — Production auth-bypass guard keyed on generic CI env var

**Plan source**: self-authored (no CodeRabbit plan on the issue; enrichment comment only).
**Approved**: autonomously (no architectural fork — the AC's "and/or" is an equivalent-options choice; the purpose-built flag is the stronger, simpler branch).

## Problem

`frontend/src/middleware.ts:19-26` — the FATAL guard fires only when
`bypassAuth && NODE_ENV==='production' && !isCI`, where `isCI = process.env.CI === 'true'`.
`CI=true` is set by most CI/PaaS/container runtimes, so a production artifact running with
`CI=true` and `BYPASS_AUTH=true` silently disables auth. The E2E infra
(`playwright.config.ts:85,91,102-103`) deliberately drives a prod build (`npm run build && npm start`)
through this hole by forwarding `CI`.

## Design decision (autonomous — AC says "and/or")

AC offers: purpose-built flag (`E2E_ALLOW_BYPASS=1`) **and/or** require `NEXT_PUBLIC_ENVIRONMENT==='test'`.
Taking the **purpose-built flag only** branch:
- `E2E_ALLOW_BYPASS=1` is opt-in, never present in real deploys, and grep-ably single-purpose.
- `NEXT_PUBLIC_ENVIRONMENT` is a general-purpose var (also used for staging labeling); keying a
  security guard on it re-creates the same "generic env var" defect class this issue removes.
- The `CI` env var is no longer consulted anywhere in the guard.

Dev-mode behavior unchanged: `BYPASS_AUTH=true` alone still bypasses when `NODE_ENV !== 'production'`
(local `npm run dev` workflows, jest, dev-mode playwright runs). The hardening targets production builds —
exactly the AC's second bullet.

## Steps (TDD)

- [ ] 1. RED: extend `frontend/src/__tests__/middleware.test.ts` with a production-guard describe:
  - `NODE_ENV=production` + `BYPASS_AUTH=true` + `CI=true` → **throws** (the regression pin for this bug)
  - `NODE_ENV=production` + `BYPASS_AUTH=true` (nothing else) → throws
  - `NODE_ENV=production` + `BYPASS_AUTH=true` + `E2E_ALLOW_BYPASS=1` → bypasses (200, no redirect)
  - `NODE_ENV=test` + `BYPASS_AUTH=true` → still bypasses without the flag (no local-workflow breakage)
- [ ] 2. GREEN: `middleware.ts` — replace `isCI` with `E2E_ALLOW_BYPASS === '1'`; guard fatal for
  `NODE_ENV==='production'` regardless of `CI`; update comments.
- [ ] 3. `playwright.config.ts` webServer env: replace the `CI` passthrough with `E2E_ALLOW_BYPASS: '1'`
  so the CI prod-build E2E run opts in explicitly.
- [ ] 4. Quality gate: frontend jest suite + lint + typecheck; opencode (GLM) pre-PR review.
- [ ] 5. Demo (hard gate): prod build + `npm start` with `BYPASS_AUTH=true CI=true` → middleware FATAL
  (auth NOT silently disabled); same build with `E2E_ALLOW_BYPASS=1` → bypass works; no-bypass prod
  run → normal redirect-to-sign-in.
- [ ] 6. PR, post-PR review, CI green, docs sync, merge.

## Acceptance criteria

- [ ] Bypass gated on a purpose-built flag (`E2E_ALLOW_BYPASS=1`) never present in real deploys
- [ ] Guard stays fatal for `NODE_ENV==='production'` regardless of `CI`

## Out of scope

- Client-side `NEXT_PUBLIC_BYPASS_AUTH` (`ProtectedRoute`, dashboard `isE2EMode`) — build-time-baked,
  different mechanism, not named by the issue.
- Backend `BYPASS_AUTH` guard (`config.py`, hardened in #176) — separate system, keyed on
  `ENVIRONMENT`/`NODE_ENV`, not `CI`.
- `deploy-staging.yml`'s BYPASS_AUTH secret check — independent defense-in-depth, unchanged.
