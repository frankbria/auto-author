# Issue #339 — Session cookie `sameSite:"none"` removes CSRF protection

Branch: `feature/339-samesite-lax-csrf`

## Finding (verified, not assumed)

- `backend/app/core/better_auth_session.py:48` authenticates from `request.cookies` →
  the backend is a genuine CSRF target.
- Multipart POSTs (`/users/me/avatar`, book cover) are CORS-"simple" → no preflight →
  a cross-site form POST executes server-side; CORS only blocks reading the response.
- Topology is **same-site everywhere**, so `lax` costs nothing:
  - `localhost:3000` → `localhost:8000` (same host; port is irrelevant to same-site)
  - `dev.autoauthor.app` → `api.dev.autoauthor.app` (registrable domain `autoauthor.app`)
- No social providers / webhooks (`auth.ts` is email+password + `twoFactor()` only),
  so there is no cross-site POST-back that `lax` would break. AC #2 is therefore N/A.
- Starlette 0.47.2 `CORSMiddleware` reflects the requested origin when
  `allow_all_origins and has_cookie` → `BACKEND_CORS_ORIGINS="*"` + `allow_credentials`
  would reflect arbitrary origins. Justifies AC #3 as a runtime guard, not just a test.

## Steps

1. **Frontend cookie attributes (TDD)**
   - New `frontend/src/lib/auth-cookies.ts`: move `getCookieDomain()` out of `auth.ts`
     and add `getDefaultCookieAttributes()` returning `sameSite:"lax"`.
     Rationale: `auth.ts` imports `server-only` + `mongodb`, so it is not unit-testable
     under jsdom. A small pure module is the smallest change that makes the security
     attribute assertable — no jest config changes, no mongo, no mocking.
   - `auth.ts` imports it (behavioral change: `none` → `lax`; `secure`/`httpOnly`/`domain` unchanged).
   - Tests: `frontend/src/lib/__tests__/auth-cookies.test.ts`

2. **Backend wildcard-CORS guard (TDD)**
   - Extend the existing `validate_production_security()` in `backend/app/main.py`
     (reuses the established fail-fast pattern) to reject `*` in `BACKEND_CORS_ORIGINS`:
     fatal `RuntimeError` in production, loud warning elsewhere.
   - Tests: `backend/tests/test_main.py`

3. **Docs**
   - `docs/session-management.md:166` already documents `sameSite:"lax"` — the code had
     drifted from the doc. Verify and add the CSRF rationale.
   - Append entry to `docs/CHANGELOG.md`.

## Acceptance criteria

- [ ] Change `sameSite` to `"lax"` (topology is same-site).
- [ ] N/A — no genuinely cross-site case exists; documented above. (If one appears
      later, the fallback is `none` + double-submit token or Origin allowlist.)
- [ ] Verify CORS does not reflect arbitrary origins.

## Known limitations

- `lax` does not defend against a same-site attacker (XSS on a sibling subdomain of
  `autoauthor.app`). Out of scope for this issue.
