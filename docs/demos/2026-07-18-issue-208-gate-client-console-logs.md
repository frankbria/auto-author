# Demo — #208: gate client `console.log` debug statements behind a dev-only logger

**PR:** #314 · **Type:** frontend-only · **Change:** new `lib/logger.ts` + `console.log` → `logger.debug` across client hooks/components.

The issue: ~2 dozen ungated `console.log` calls printed internal client state to the
production browser console. AC: *route through a dev-only logger gated on
`process.env.NODE_ENV`; keep genuine `console.error`/`console.warn`.*

---

## AC 1 — ungated debug logs no longer run in the production browser

**Mechanism:** `logger.debug` calls `console.log` only when `process.env.NODE_ENV !== 'production'`.
In a production build Next.js inlines `NODE_ENV`, so the guard is `if (false)` → the log never executes.

**Outcome (real module, real runtime gate — `lib/__tests__/logger.test.ts`):**

```
✓ does not call console.log in production      (0 console.log calls under NODE_ENV=production)
✓ calls console.log with all args outside production
✓ also logs under test env (non-production)
```

**No ungated debug `console.log` remain in client production code** (grep over
`src/**/*.{ts,tsx}`, excluding server files / JSDoc comments / test helpers):

```
=== remaining EXECUTED console.log in client production code ===
lib/logger.ts:15:      console.log(...args);      # the single gated call, by design
```

## AC 2 — genuine `console.error` / `console.warn` preserved

Only `console.log` was converted. A real `console.error` string survives into the
production client bundle:

```
'Verification query failed' (a console.error) → present in .next/static  (1 file)
```

## Build / suites

- `npm run build` → exit 0 (production build succeeds).
- 15 affected hook/component suites → **244 passed**; new `logger.test.ts` → 3 passed.
- Typecheck clean; lint 0 errors.

## Scope note

Server code (`lib/auth.ts`, `lib/email.ts`), JSDoc `* console.log` examples, and
`lib/testing/*` / `e2e/*` helpers are out of scope — they never ship to the browser.
The two client files the issue didn't list (`NotReadyMessage.tsx`,
`chapters/[chapterId]/page.tsx`) were included as the same class (root-cause completeness).
