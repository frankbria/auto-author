# Issue #190 [P1.10] — CSP ships unsafe-inline/unsafe-eval and dead Clerk origins

**Branch**: `fix/issue-190-csp-hardening` · frontend-only · security
**Plan source**: self-authored (no plan comment on the issue).
**Approved**: autonomously (no architectural fork — the AC mandates nonces; middleware-nonce + `strict-dynamic` is the single documented Next.js approach).

## Problem
`frontend/next.config.ts` ships a static CSP with `script-src 'unsafe-eval' 'unsafe-inline'` (neutering CSP as an XSS mitigation while the app renders AI/user-derived HTML via `dangerouslySetInnerHTML`), dead Clerk origins (`clerk.auto-author.dev`, `*.clerk.accounts.dev`, `clerk-telemetry.com` — app migrated to better-auth 2025-12), and `http://localhost:8000`/`wss:` in production connect-src.

## Acceptance criteria (from issue)
1. Drop `'unsafe-inline'`/`'unsafe-eval'` from script-src (nonces/hashes for required inline scripts)
2. Remove all `clerk.*` / `clerk-telemetry` entries
3. Drop `http://localhost:8000` / `wss:` from production connect-src

## Approach: middleware-generated per-request nonce (official Next.js 15 pattern, verified via context7)
A static `headers()` CSP can't carry a per-request nonce, so the CSP moves from `next.config.ts` to `src/middleware.ts`. Next.js extracts the nonce from the CSP **request** header and stamps its own inline bootstrap scripts automatically (dynamic rendering required).

### Evidence gathered
- `next-themes` `ThemeProvider` (root layout) injects an inline theme script → needs the nonce (supports `nonce` prop). No other app-authored inline scripts.
- No WebSockets in app code → `wss:` is dead. Dev HMR is webpack `ws://localhost:3000` (dev-only CSP branch).
- Fonts self-hosted via `next/font` → `fonts.googleapis.com`/`fonts.gstatic.com` dead. `r2cdn.perplexity.ai` (font-src) and `challenges.cloudflare.com` (Clerk-era captcha; no Turnstile in codebase) dead. `https://api.auto-author.dev` is the pre-migration domain — dead.
- No `<iframe>` in src → drop `frame-src` (falls back to `default-src 'self'`).
- `NEXT_PUBLIC_API_URL` is set at build time by all deploy paths (deploy-staging.yml, ecosystem template, legacy scripts) AND by CI E2E (`tests.yml:203` → `http://localhost:8000/api/v1`) → **derive connect-src from it** (same fallback as `bookClient.ts:46`). Prod deploys get only the real API origin; CI E2E keeps localhost automatically; no generic-env keying (#192 lesson).
- styled-components + Tailwind inline styles → style-src keeps `'unsafe-inline'` **without** a nonce (a nonce in style-src makes browsers ignore unsafe-inline → would break all inline styles). Documented accepted risk; AC targets script-src.

### Steps (TDD)
- [x] 1. **RED**: `src/lib/__tests__/csp.test.ts` — pure `buildCsp(nonce, {isDev, apiUrl})`:
  - prod script-src = `'self' 'nonce-X' 'strict-dynamic'`, no unsafe-inline/unsafe-eval
  - dev script-src additionally has `'unsafe-eval'` (webpack HMR) — official Next.js conditional
  - no `clerk`/`clerk-telemetry`/`cloudflare`/`perplexity`/`googleapis`/`gstatic`/`auto-author.dev` substrings anywhere
  - connect-src = `'self'` + origin(NEXT_PUBLIC_API_URL); no `wss:`; localhost only when apiUrl is localhost (the CI/dev shape); dev adds `ws://localhost:*` for HMR
  - no frame-src; object-src 'none', base-uri/form-action 'self', frame-ancestors 'none' preserved
- [x] 2. **RED**: extend `src/__tests__/middleware.test.ts` — response carries CSP header (public + protected-authed paths, and the BYPASS_AUTH early-return path), `x-nonce` request header forwarded (and overwrites any client-sent value), nonce unique across two requests, script-src clean of unsafe-*
- [x] 3. **GREEN**: new `src/lib/csp.ts` (pure builder); wire into `middleware.ts` (nonce = base64 UUID; set CSP on request+response per official pattern — on every code path incl. bypass); auth logic unchanged
- [x] 4. **GREEN**: `next.config.ts` — delete the CSP entry from `headers()` (other security headers stay); `src/app/layout.tsx` — async RootLayout reads `(await headers()).get('x-nonce')`, passes `nonce` to `ThemeProvider`
- [x] 5. Full frontend suite + lint + typecheck; prod build sanity (`npm run build`)
- [x] 6. Deslop scan; opencode (GLM) pre-PR review; PR
- [x] 7. **Demo (hard gate)**: main vs branch prod builds — (a) curl shows old header with unsafe-*/clerk vs new nonce'd header; (b) real browser load on the branch: page renders, **zero CSP violations in console**, dark theme applied pre-hydration (nonce'd theme script ran), sign-in→dashboard round trip against real backend on localhost:8000 (proves derived connect-src); (c) nonce changes per request
- [x] 8. CI green + post-PR review triage; docs sync (CLAUDE.md changelog); merge

### Accepted tradeoffs (documented in PR)
- **All routes render dynamically** (nonce requires it; `headers()` in root layout forces it). App is auth-gated + VPS-served; static optimization loss is acceptable. This is the documented cost of the official pattern.
- **style-src keeps 'unsafe-inline'** — inline-style injection is a far weaker primitive than script injection; required by styled-components/Tailwind/TipTap. AC targets script-src.
- Dev CSP keeps `'unsafe-eval'` (webpack) — matches the official Next.js example; production never gets it.

## Issue #265 — PUT /users/{auth_id} skips sanitize_input (P1.13)
- [ ] RED: test — markup string stored identically (sanitized) via PATCH /me and PUT /{auth_id}
- [ ] Shared helper `sanitize_string_fields` in users.py; wire into both endpoints
- [ ] GREEN: users test file + full backend gates
- [ ] opencode pre-PR review → PR → post-PR review → demo → CI → merge
