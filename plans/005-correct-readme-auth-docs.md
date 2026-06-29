# Plan 005: README documents the real (better-auth) authentication, not Clerk

> **Executor instructions**: Follow step by step. Run each verification command
> and confirm before moving on. STOP and report on any STOP condition. Update
> `plans/README.md` when done unless a reviewer maintains the index.
>
> **Drift check (run first)**: `git diff --stat e6980f3..HEAD -- README.md`
> Compare the "Current state" excerpts to live README; mismatch → STOP.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: docs
- **Planned at**: commit `e6980f3`, 2026-06-21
- **Issue**: https://github.com/frankbria/auto-author/issues/89

## Why this matters

This is a **public** repository, and its README — the project's front page —
still documents Clerk as the auth provider. The codebase migrated from Clerk to
better-auth months ago (cookie-based sessions, HS256, `auth_id` instead of
`clerk_id`); see `CLAUDE.md` entries dated 2025-12-17 and 2025-12-24. The
README's auth section, tech-stack table, env-var examples (`CLERK_SECRET_KEY`,
`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`), and several doc links all describe a
system that no longer exists and point to files that aren't in the repo. New
contributors and users following these instructions will configure the wrong
thing. Correcting it is cheap and removes active misinformation from a public
surface.

## Current state

**Ground truth (verified in code):**
- Auth is better-auth with httpOnly **session cookies** (no JWT on the wire to
  the backend). Backend validates the session cookie against MongoDB:
  `backend/app/core/better_auth_session.py` (cookie names
  `__Secure-better-auth.session_token` / `better-auth.session_token`).
- User identity field is `auth_id` (with a legacy `clerk_id` fallback still
  present — see plan: "Clerk→better-auth cleanup", a separate direction item).
- Required env vars are `BETTER_AUTH_SECRET` and `BETTER_AUTH_URL`
  (see `backend/app/core/config.py` and `backend/.env.example` /
  `frontend/.env.example`). `BYPASS_AUTH=true` is dev/E2E-only and is rejected
  in production by `config.py`.
- There are **no** Clerk packages or `NEXT_PUBLIC_CLERK_*` vars in the code.

**Stale README content to fix** (line numbers at `e6980f3`):
- `README.md:19` — `* 🔐 Secure **user authentication** with Clerk and profile management`
- `README.md:46` — tech-stack table row: `| Auth | Clerk Authentication |`
- `README.md:48` — `| Voice Input | Web Speech API / Whisper API |` (this is
  fine — leave it; listed only for context)
- `README.md:52-90` — the entire `## 🔐 Authentication with Clerk` section
  (describes Clerk, JWKS endpoint, and links to non-existent docs:
  `docs/clerk-integration-guide.md`, `docs/user-guide-auth.md`,
  `docs/clerk-deployment-checklist.md`, `docs/profile-management-guide.md`,
  `docs/api-profile-endpoints.md`).
- `README.md:154-155` and `README.md:164-165` — env-var examples listing
  `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`,
  `CLERK_WEBHOOK_SECRET`.
- `README.md:396` and `README.md:408` — doc links referencing the Clerk guide
  and deployment checklist.
- `README.md:449` — `* User authentication and profile management with Clerk`
- `README.md:509` — changelog line: `JWT Verification Enhancement: Migrated ...
  to Clerk's JWKS endpoint ...`

Before editing, re-grep to get the authoritative current line numbers:
`grep -ni "clerk" README.md`.

## Commands you will need

| Purpose          | Command                          | Expected                     |
|------------------|----------------------------------|------------------------------|
| Find references  | `grep -ni "clerk" README.md`     | lists all Clerk mentions     |
| Verify env names | `grep -n "BETTER_AUTH" backend/.env.example frontend/.env.example` | shows real var names |

## Scope

**In scope**:
- `README.md` only.

**Out of scope** (do NOT touch):
- `CLAUDE.md` (its migration changelog is intentionally historical).
- Code, `.env.example` files, or any `docs/*` file.
- The legacy `clerk_id` fallback in code (separate direction item — do not
  remove code here).
- README sections unrelated to auth (features unrelated to Clerk, setup steps
  for Node/Python, etc.) beyond the specific lines listed.

## Git workflow

- Branch: `advisor/005-correct-readme-auth-docs`
- Conventional commit, e.g. `docs: correct README to reflect better-auth (not Clerk)`.
- Do NOT push or open a PR unless instructed.

## Steps

### Step 1: Re-discover current line numbers

Run `grep -ni "clerk" README.md`. Use these live results (not the SHA-stamped
numbers above, which may have shifted) as your edit map.

### Step 2: Fix the one-line mentions

- `:19` feature bullet → `* 🔐 Secure **user authentication** (better-auth) and profile management`
- tech-stack table Auth row → `| Auth | better-auth (cookie sessions) |`
- `:449` → `* User authentication and profile management with better-auth`
- `:509` changelog line → leave the historical fact but mark it superseded, e.g.
  append `(later replaced by better-auth — see CLAUDE.md 2025-12-17)`.

### Step 3: Rewrite the Authentication section (current lines ~52–90)

Replace the whole `## 🔐 Authentication with Clerk` section with a better-auth
description. Target content (adapt prose to match README tone):
```markdown
## 🔐 Authentication (better-auth)

Auto Author uses [better-auth](https://www.better-auth.com/) for
authentication with cookie-based sessions:

- Email/password registration and login, email verification, password reset
- httpOnly session cookies (no JWT is sent to the backend)
- Sessions stored in MongoDB; the backend validates the session cookie on each
  request (see `backend/app/core/better_auth_session.py`)

We keep a local user record in MongoDB keyed by the better-auth user id
(`auth_id`) so books, chapters, and preferences can be associated with a user.

### Configuration

- Backend: `BETTER_AUTH_SECRET` (≥32 chars; ≥64 in production),
  `BETTER_AUTH_URL` — see `backend/.env.example`.
- Frontend: see `frontend/.env.example`.
- `BYPASS_AUTH=true` enables auth bypass for local development and E2E tests
  only. It is rejected at startup in production.

> Migration note: this project previously used Clerk. See `CLAUDE.md`
> (2025-12-17 and 2025-12-24) for migration details.
```
Remove all five dead `docs/clerk-*` / `docs/*-auth*` links.

### Step 4: Fix the env-var example blocks (current lines ~154–165)

Remove the `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`, and
`CLERK_WEBHOOK_SECRET` lines. Replace with the real variables, sourced from the
`.env.example` files (run the verify command). At minimum include
`BETTER_AUTH_SECRET=...` and `BETTER_AUTH_URL=...`. Do not invent variable
names — copy them from `backend/.env.example` / `frontend/.env.example`.

### Step 5: Fix the doc links (current lines ~396, ~408)

Remove links to `docs/clerk-integration-guide.md` and
`docs/clerk-deployment-checklist.md` (the files do not exist). If a replacement
exists in `docs/`, link it; otherwise drop the bullet.

**Verify**: `grep -ni "clerk" README.md` → returns at most the single,
explicitly-marked historical migration note (Step 2), and nothing else.

## Test plan

Docs-only; no code tests. Verification is the grep below plus a manual read of
the rewritten section for accuracy against `better_auth_session.py` and the
`.env.example` files.

## Done criteria

ALL must hold:

- [ ] `grep -ni "clerk" README.md` returns only the one historical migration
      note (or zero matches)
- [ ] `grep -n "CLERK_SECRET_KEY\|NEXT_PUBLIC_CLERK" README.md` → no matches
- [ ] README references `BETTER_AUTH_SECRET` and `BETTER_AUTH_URL`
- [ ] No dead `docs/clerk-*.md` links remain (`grep -n "docs/clerk" README.md` → none)
- [ ] Only `README.md` changed (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report if:
- The `.env.example` files reveal auth variables not described here (report the
  real set so the README matches reality).
- README structure differs substantially from the excerpts (drift) — re-map
  via grep and, if the auth section is already partly rewritten, report rather
  than duplicate.

## Maintenance notes

- Keep README auth claims in sync with `backend/app/core/config.py` and the
  `.env.example` files on any future auth change.
- A follow-up (separate item) removes the legacy `clerk_id` fallback from code;
  when that lands, the historical note here can stay but the code reference is
  gone.
