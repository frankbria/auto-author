# Session Management Strategies

This document outlines the session management approaches used in Auto Author, providing guidance for both developers and system administrators.

## Overview

Auto Author uses better-auth for sign-in and sessions. The frontend runs better-auth and stores sessions in MongoDB. The FastAPI backend reads the same session from the database. There are no JWTs and no Authorization header: the browser sends the session cookie.

## How a request is authenticated

1. Sign-in sets an httpOnly session cookie (`better-auth.session_token`, or `__Secure-better-auth.session_token` over HTTPS).
2. The backend (`app/core/better_auth_session.py`) checks the cookie's signature with `BETTER_AUTH_SECRET`, then looks the session up in MongoDB by token and joins its user.
3. It rejects the request if the session has expired, the user row is gone, or the account is deactivated (`app/core/security.py`, `get_current_user_from_session`).

A session ends when the user signs out, when it expires, when it is revoked from Settings, or when a password reset revokes every session of the account.

## Sign-in and Sign-out Behavior

- **Sign-in** (`/auth/sign-in`): email and password. On success the user goes to the `?redirect=` target, or `/dashboard` when none is given. The redirect is sanitized to a same-site path. An unverified account is refused with `403 EMAIL_NOT_VERIFIED` and sent a fresh verification link.
- **Protected routes**: `src/middleware.ts` guards `/dashboard` and `/profile`. It only checks that a session cookie exists; the backend validates the session on each API call. With no cookie the user is redirected to `/auth/sign-in?redirect=<path>`.
- **Sign-out**: "Sign out" in the account menu calls `signOutOrNotify()` (`src/lib/sign-out.ts`) and goes to the home page only once the session is really gone. If the request fails, a "Could not sign out" toast says the user is still signed in.
- **Backend 401**: `apiFetch()` (`src/lib/api/unauthorized.ts`) signs the browser out and redirects to `/auth/sign-in?redirect=<current page>`. This covers a session that expired, was revoked from another device, or belongs to a closed account.
- **Multiple devices**: Settings lists active sessions and can revoke one or all others (`ActiveSessionsList`, using better-auth's `listSessions`, `revokeSession` and `revokeOtherSessions`). Resetting a password ends every session of the account.

## Session Duration

There is one kind of session. It lasts 7 days (`expiresIn`) and is renewed at most once every 24 hours while the user is active (`updateAge`). Both values are in `src/lib/auth.ts`. There is no "remember me" option.

## Security Measures

- **Signature check**: the backend accepts a cookie only if its signature matches `BETTER_AUTH_SECRET`, so the token alone does not authenticate.
- **Cookie attributes**: httpOnly, `secure`, `sameSite: lax` (see Cookie Settings below).
- **No cookie cache**: `auth.ts` has no `cookieCache`, so a revoked session stops working at once instead of lingering for minutes (#793).
- **Password reset**: ends every session of the account (`revokeSessionsOnPasswordReset`) and forgets every device trusted to skip the second factor (#972).
- **Two-factor changes**: enabling 2FA (the `verify-totp` call that completes setup), disabling it and regenerating backup codes end every other session of the account in the same request; disabling also forgets every trusted device (#972, `src/lib/auth-second-factor.ts`). The `verify-totp` or backup-code call that finishes a sign-in ends nothing.
- **Secret rotation**: the backend knows one secret only. Changing `BETTER_AUTH_SECRET` signs every user out.

## Two-factor response flags (API contract)

`POST /api/auth/two-factor/verify-totp` (when it enables 2FA), `POST /api/auth/two-factor/disable` and `POST /api/auth/two-factor/generate-backup-codes` answer 200 once the change itself is made, even when a follow-up step failed. The follow-up is retried once and the failure is logged and sent to Sentry; the answer then carries better-auth's usual body plus:

| Field | Endpoints | Meaning when `false` |
|---|---|---|
| `otherSessionsEnded` | all three | The account's other sessions are still signed in. |
| `trustedDevicesForgotten` | `disable` | Devices trusted earlier may skip the code if 2FA is turned back on. |

Each field is present only when it is `false`; absent means the step succeeded. Every caller must check them: a 200 alone does not mean the other devices are signed out. The settings page (`TwoFactorSetup.tsx`) shows a warning toast for each. The change is not answered with an error instead, because it has already happened, and an error would lose freshly regenerated backup codes.

## Configuration Options

### Core Authentication Settings

Essential better-auth environment variables:

```bash
# Authentication secret (required) - better-auth signs its session cookies with it, and the backend checks that signature
BETTER_AUTH_SECRET=your-secret-key-min-32-chars

# Base URL for your application
BETTER_AUTH_URL=http://localhost:3000

# Database connection (MongoDB)
DATABASE_URL=mongodb://localhost:27017/auto_author
DATABASE_NAME=auto_author
```

### Session Timeouts

Session configuration is defined in `src/lib/auth.ts`:

```typescript
session: {
  expiresIn: 60 * 60 * 24 * 7,  // 7 days (604,800 seconds)
  updateAge: 60 * 60 * 24,       // Refresh every 24 hours
  // No cookieCache (#793)
},
```

### Cookie Settings

Session cookie configuration lives in `src/lib/auth-cookies.ts` (kept out of
`src/lib/auth.ts` so the attributes stay unit-testable — `auth.ts` imports
`server-only` and the MongoDB driver):

```typescript
advanced: {
  defaultCookieAttributes: {
    sameSite: "lax",         // CSRF protection (issue #339)
    secure: true,            // HTTPS only; localhost is a trustworthy origin
    httpOnly: true,          // Not readable from JS
    domain: getCookieDomain(), // ".dev.autoauthor.app" in staging; undefined (host-only) on localhost or an apex
  },
}
```

**Cookie domain (issue #778):** the domain is `.${host}` of `BETTER_AUTH_URL`, so
`dev.autoauthor.app` shares the cookie with `api.dev.autoauthor.app`. An apex host
(`autoauthor.app`) is never widened to `.autoauthor.app`, because that domain
matches every subdomain, including the shared staging box. An apex gets a
host-only cookie instead, so production must either live on a subdomain
(`app.autoauthor.app` with the API at `api.app.autoauthor.app`) or serve the API
from the same host.

**Why `lax` and not `none`:** the backend authenticates from `request.cookies`,
and multipart uploads (avatar, book cover) are CORS-"simple" requests that trigger
no preflight — under `"none"` a cross-site form POST would carry the victim's
session cookie and execute server-side, because CORS blocks *reading* the response
but not the write. `"lax"` costs nothing because every frontend→backend hop is
same-site (same-site is computed on the registrable domain and ignores
port/subdomain): `localhost:3000 → localhost:8000` and
`dev.autoauthor.app → api.dev.autoauthor.app` (both `autoauthor.app`).

Returning to `"none"` would require a genuinely cross-site topology *and* a
compensating control — a double-submit CSRF token or an explicit Origin allowlist
check on state-changing methods.

### Rate Limiting

`auth.ts` sets no custom rate-limit rules, so better-auth's own defaults apply to its endpoints (in production, sign-in is capped at a few attempts per ten seconds per client).

## Developer Usage

### Frontend Session Management

```typescript
// Check authentication state
import { useSession } from '@/lib/auth-client';

export function MyComponent() {
  const { data: session, isPending } = useSession();

  if (isPending) {
    return <div>Loading...</div>;
  }

  if (!session) {
    return <div>Please sign in</div>;
  }

  return <div>Welcome, {session.user.name || session.user.email}</div>;
}
```

### Backend Session Verification

```python
from fastapi import Depends
from app.core.security import get_current_user_from_session

@router.get("/protected-endpoint")
async def protected_endpoint(current_user = Depends(get_current_user_from_session)):
    return {"message": f"Hello, {current_user['email']}"}
```

## Related Documentation

- [Authentication User Guide](../user-guide/auth.md), including troubleshooting
- [Profile API](../api/profile.md), including authentication
