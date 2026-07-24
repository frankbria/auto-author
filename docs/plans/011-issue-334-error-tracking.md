# Plan 011 — Issue #334: Error tracking + observability (P1.2)

**Self-authored** (issue had no plan comment). Labels: high, reliability, observability.

## Acceptance criteria
1. Add Sentry SDK to both apps (`sentry-sdk[fastapi]` + `@sentry/nextjs`).
2. `logger.warning` before each 429 raise with subject/path/limit.
3. Point the perf-metrics production branch at a real sink or drop the localStorage-only path.

## Design decisions
- **DSN-gated, inert by default.** Sentry init is a no-op when the DSN env var is
  unset, so CI/local/tests get no new behavior or failure mode. Ops sets the DSN
  secret to turn it on (same pattern as `EMAIL_*`/`STRIPE_*`).
- **Lean `@sentry/nextjs`, no `withSentryConfig`.** Error capture needs only
  `Sentry.init` (client via `instrumentation-client.ts`, server via
  `instrumentation.ts`), `onRequestError`, and `captureException` in the App
  Router error boundaries. `withSentryConfig` only adds build-time source-map
  upload (needs an auth token) + tunneling — nice-to-haves that add build risk
  against this project's nonce-CSP + styled-components SWC. Deferred to ops.
- **AC2 scope = the two `dependencies.py` 429s** (rate limiter #180, AI quota
  #173) — the ones the issue names that emit no log. The `books.py`
  `AIRateLimitError` re-raises are already logged at the AI-service layer with a
  correlation id, so they are not re-logged.
- **AC3 = both halves of the OR.** Drop the localStorage-only write (a write-only
  path nothing shipped) AND route production `poor`-rated metrics to Sentry.
  `getCachedMetrics`/`clearCachedMetrics` only served the dropped path (no
  product consumers) → deleted per the dead-code precedent (#200/#209/#295).

## Steps
### Backend
1. `pyproject.toml`: add `sentry-sdk[fastapi]==2.66.1`; `uv lock`.
2. `config.py`: add `SENTRY_DSN: str = ""` (+ strip validator).
3. `main.py`: `sentry_sdk.init(...)` gated on `settings.SENTRY_DSN`; add
   `sentry_sdk.capture_exception(exc)` in the global 500 handler (the choke point
   — our handler catches the exception so the ASGI integration wouldn't see it).
4. `dependencies.py`: module logger + `logger.warning` before both 429 raises
   with subject/path/limit; add `request: Request` to the quota dep for the path.
5. `.env.example` + `deploy-staging.yml`: wire `SENTRY_DSN` secret.

### Frontend
6. `package.json`: add `@sentry/nextjs@^10.67.0`; `npm install`.
7. `src/instrumentation.ts` (server/edge init + `onRequestError`) and
   `src/instrumentation-client.ts` (client init), DSN-gated.
8. `src/app/error.tsx`: `Sentry.captureException`; new `src/app/global-error.tsx`.
9. `src/lib/performance/metrics.ts`: production branch → `Sentry.captureMessage`
   for `poor` metrics; delete localStorage write + `getCachedMetrics`/
   `clearCachedMetrics`.
10. `src/lib/csp.ts`: add the Sentry ingest origin to `connect-src` when a DSN is
    configured (else the browser CSP blocks event delivery in production).
11. `.env.example` + `deploy-staging.yml`: wire `NEXT_PUBLIC_SENTRY_DSN`.
12. `jest`: `__mocks__/sentry-nextjs.ts` + moduleNameMapper so tests stay
    deterministic and don't import the real SDK.

## Tests
- Backend: `test_dependencies.py` caplog assertions for both 429 warnings;
  `main.py` global handler calls `capture_exception`; `SENTRY_DSN` config default.
- Frontend: `metrics.test.ts` rewrite (poor→Sentry, good→not; localStorage tests
  removed); `csp.test.ts` Sentry-origin-in-connect-src; `error`/`global-error`
  captureException.

## Known limitations
- Sink is live only once the DSN secret is set (an ops step) — same as the
  existing email/Stripe env plumbing.
- No source-map upload (no `withSentryConfig`); server stack traces are readable,
  client ones are minified until ops adds the Sentry build plugin + auth token.
