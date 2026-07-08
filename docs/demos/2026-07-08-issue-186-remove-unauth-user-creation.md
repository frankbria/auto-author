# Demo — Issue #186: Remove unauthenticated `POST /users/` enumeration oracle

**Date:** 2026-07-08
**PR:** #240
**Setup:** two real `uvicorn app.main:app` servers against a local mongod — `main`
(vulnerable, worktree, :8801) and the fix branch (:8802), each with its own DB.
All requests below are **anonymous** (no session cookie) — the endpoint had no auth.

## Acceptance criterion
> Endpoint requires auth/authorization or is removed; if kept, uniform response
> that doesn't distinguish exists/created, and rate-limited.

Fix takes the **"or is removed"** branch.

## Evidence

### `main` — the oracle (and unauthenticated junk-record insertion)
| Request (anonymous) | Response |
|---|---|
| `POST /api/v1/users/` new identity | **`201 Created`** — record inserted |
| `POST` same `auth_id` again | **`409 "User with this auth ID already exists"`** |
| `POST` different `auth_id`, same `email` | **`409 "User with this email already exists"`** |
| `POST` fresh identity → count in DB | **1 record created** by an anonymous caller |

An unauthenticated attacker learns from the status + message whether any given
`auth_id` or `email` is registered, and can freely insert records.

### fix branch — endpoint removed, uniform `404`
| Request (anonymous) | Response |
|---|---|
| `POST /api/v1/users/` new identity | **`404 Not Found`** |
| `POST` an **existing** identity (seeded directly into the DB) | **`404 Not Found`** — identical |
| `POST` different `auth_id`, same existing `email` | **`404 Not Found`** — identical |
| `POST` fresh identity → count in DB | **0 records created** |

Identical `404` regardless of whether the identity exists → **no enumeration
signal**. `0` records created → **junk-record vector closed**. Real signup is
unaffected (it rides the better-auth session auto-create in
`app/core/security.py`, not this route).

## Result
✅ Oracle eliminated, junk-record insertion eliminated, no behavior change for
any real caller (there were none). Backend suite 1102 passed / 13 skipped,
92.03% coverage; opencode pre-PR review clean.
