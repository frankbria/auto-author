# [P2.22] #272 — Require E2E_ALLOW_BYPASS for auth bypass in ALL environments

**Plan source**: self-authored (issue has acceptance criteria but no step plan; no comments).
**Approval**: autonomous — no architectural fork.

## Design decisions (autonomous — safe defaults)

1. **Non-prod, `BYPASS_AUTH=true` without the flag** → bypass is *ignored* (fall through to
   normal auth) + `console.warn` explaining `E2E_ALLOW_BYPASS=1` is required. No FATAL outside
   production — the prod FATAL (`middleware.ts:42-48`) stays exactly as-is as the loud layer.
2. **Backend (FastAPI) `BYPASS_AUTH` system is OUT of scope** — parallel guard with its own
   semantics, untouched by #271; the issue and all AC items are about the Next.js middleware.
3. **`NEXT_PUBLIC_BYPASS_AUTH` (client var) is OUT of scope** — used by
   `ProtectedRoute.tsx`/`dashboard/page.tsx`, not the middleware path; issue doesn't mention it.
4. **`.env.test`** is gitignored and absent on disk (dotenv load is a silent no-op). Tracked
   counterpart updated instead: `frontend/.env.example` documents the both-required rule.
   `playwright.config.ts:103` already hardcodes `E2E_ALLOW_BYPASS: '1'` in webServer env — no change.
5. **Pre-commit hook** (`.pre-commit-config.yaml:75`) unchanged — it invokes Playwright, which
   supplies the flag via webServer env.

## Steps

- [ ] 1. **TDD pins** — `frontend/src/__tests__/middleware.test.ts`:
  - [ ] invert `'still bypasses outside production without the flag'` (:115-120) → now must NOT bypass
  - [ ] new pins: `BYPASS_AUTH=true` alone with `NODE_ENV` = test / development / unset → no bypass
  - [ ] `BYPASS_AUTH=true` + `E2E_ALLOW_BYPASS=1` in non-prod → bypass works
  - [ ] prod FATAL without flag unchanged; prod + flag bypasses (existing pins)
  - [ ] flag alone (no `BYPASS_AUTH`) → no bypass (existing pins :108-131, adjust if needed)
  - [ ] CSP describe (:168-173) sets the flag too (it exercises the bypass early-return)
- [ ] 2. **Implement** — `frontend/src/middleware.ts`: gate the bypass early-return on
      `e2eAllowBypass` in every environment; add the non-prod warn-and-enforce path.
- [ ] 3. **CI** — `.github/workflows/tests.yml`: add `E2E_ALLOW_BYPASS: '1'` to the Run-E2E step env (:196-207).
- [ ] 4. **Env template** — `frontend/.env.example`: document `E2E_ALLOW_BYPASS` + both-required rule.
- [ ] 5. **Docs** — `README.md` (:71, :146-147, :162-163, :361-362),
      `frontend/tests/e2e/E2E_TEST_STATUS.md` (:163-165), `frontend/docs/E2E_TEST_STATUS.md` (:197-198),
      `CLAUDE.md` (:644, :963): add `E2E_ALLOW_BYPASS=1` to documented bypass commands + state the rule.
- [ ] 6. **Verify** — `cd frontend && npx jest src/__tests__/middleware.test.ts` green, then full
      `npm test -- --watchAll=false`, `npm run lint`, `npm run typecheck`.

## Acceptance criteria (from issue)

- [ ] `BYPASS_AUTH=true` only takes effect when `E2E_ALLOW_BYPASS=1` is also set, in every environment.
- [ ] Local/E2E workflows updated: `.env.test` (→ tracked `.env.example`; file itself is gitignored),
      `playwright.config.ts` webServer env (already sets it), documented `npm run dev` bypass
      instructions, and the CI E2E job.
- [ ] Tests pin: `BYPASS_AUTH=true` alone (any `NODE_ENV`) does not bypass.

## Known limitations / noted but out of scope

- Backend FastAPI bypass guard unchanged (see decision 2).
- Client-side `NEXT_PUBLIC_BYPASS_AUTH` unchanged (see decision 3).
- Residual: a leaked `BYPASS_AUTH=true` **plus** leaked `E2E_ALLOW_BYPASS=1` still bypasses —
  inherent to the design; the flag is purpose-built and never set by deploys.
