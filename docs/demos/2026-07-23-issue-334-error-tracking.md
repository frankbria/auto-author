# Demo — Issue #334: Error tracking + 429 logging + real perf sink (P1.2)

Outcome-evidence demo. Each acceptance criterion is shown as a **main-vs-branch
differential** run against the real code. Sentry event *delivery* is DSN-gated
(an ops step); what's demonstrated is that the wiring is real and fires — the
capture calls, the log lines, and the sink swap — where **main does none of it**.

---

## AC1 — Sentry SDK in both apps

### Backend: an unhandled 500 now routes to Sentry

`app/main.py`'s global `@app.exception_handler(Exception)` is the choke point for
every 500 (it catches the exception, so the ASGI integration alone never sees it).

```
BRANCH: unhandled 500 routing
DSN set   : handler->HTTP 500 | sentry.capture_exception called 1x
DSN unset : handler->HTTP 500 | sentry.capture_exception called 0x   # inert without a DSN

MAIN baseline: main main.py sentry/capture_exception refs: 0
```

→ On `main`, 500s die in PM2 stdout. On the branch they reach Sentry when a DSN
is set, and stay inert (no new behavior) when it isn't.

### Frontend: SDK wired, error boundaries capture

```
MAIN error.tsx Sentry refs:   0
BRANCH Sentry-wired files:     8   # instrumentation(.client).ts, error.tsx, global-error.tsx, metrics.ts, csp.ts, mock

app/error.tsx        ✓ captures the error to Sentry on mount
app/global-error.tsx ✓ captures the error to Sentry on mount
```

App Router boundary errors don't reach `window.onerror`, so the boundaries must
capture explicitly — verified above. `next build` compiles clean with the
integration (`✓ Compiled successfully`, exit 0).

### CSP allows the Sentry ingest origin only when a DSN is set

```
buildCsp — Sentry connect-src (#334)
  ✓ adds the Sentry ingest origin to connect-src when a DSN is configured
  ✓ adds no Sentry origin when no DSN is configured
  ✓ ignores an unparseable DSN (no origin added, no throw)
```

---

## AC2 — `logger.warning` before each per-user 429 (subject/path/limit)

Tripping the real per-user rate limiter on the branch:

```
LOG> WARNING app.api.dependencies: Rate limit exceeded: subject=demo-user-42 path=/api/v1/books/abc/generate-toc limit=1 window=60s count=2
HTTP> 429 Rate limit exceeded. Try again in 27 seconds.

MAIN baseline: main dependencies.py logger.warning count: 0
```

→ On `main` the 429 is silent (an abuse/quota storm is invisible). On the branch
the rate limiter **and** the AI quota each log subject/path/limit before raising.

---

## AC3 — perf-metrics production branch → real sink (localStorage-only path dropped)

```
MAIN metrics.ts localStorage refs:   7   # write-only cache nothing shipped
BRANCH metrics.ts localStorage refs: 0   # (1 remaining hit is a comment word)

Production Sentry sink (#334)
  ✓ reports a poor operation metric to Sentry as a warning
  ✓ does NOT report a good metric to Sentry (keeps noise low)
  ✓ does NOT report to Sentry in development mode
  ✓ reports a poor web vital to Sentry in production mode
  ✓ does NOT report a good web vital to Sentry in production mode
```

→ On `main`, production perf metrics were written to a localStorage cache nothing
ships. On the branch, `poor`-rated regressions go to Sentry and the dead
localStorage path (plus its orphaned `getCachedMetrics`/`clearCachedMetrics`) is
gone.

---

## Known limitations
- The sink is live only once the DSN secret is set (an ops step) — same pattern
  as the existing email/Stripe env plumbing.
- No source-map upload (no `withSentryConfig`); client stack traces are minified
  until ops adds the Sentry build plugin + auth token.
