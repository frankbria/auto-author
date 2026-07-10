# Issue #244 — PATCH /users/me role self-elevation: reproduced on main, closed on the fix branch

*2026-07-10T18:20:47Z*

Setup: two **real** uvicorn servers share one **real** MongoDB (`auto_author_demo244`), both with `BYPASS_AUTH=false` so genuine better-auth session cookies are validated against the DB.

- **:8802** runs `main` (commit e323f82, a git worktree) — the vulnerable code.
- **:8801** runs the fix branch `fix/244-role-self-elevation`.

A normal user (`role: user`) and a valid better-auth session are seeded directly into Mongo, so `PATCH /users/me` can be driven with a real session cookie — no UI needed for an API-only privilege-escalation bug.

```bash
uv run --project /home/frankbria/projects/auto-author/backend python /tmp/claude-1000/-home-frankbria-projects-auto-author/a1970958-55cf-4990-b245-4b0b467827bd/scratchpad/seed244.py
```

```output
Seeded DB=auto_author_demo244 user auth_id=demo-victim-244 role=user
```

## The attack on `main` (:8802)

A logged-in, non-admin user sends `PATCH /users/me` with `{\"role\": \"admin\"}` — the same body any browser devtools could fire — using their genuine session cookie. On main the schema accepts `role` and dumps it into a generic Mongo `$set`.

```bash
curl -s -m8 -o /dev/null -w 'HTTP %{http_code}\n' -X PATCH http://127.0.0.1:8802/api/v1/users/me -H 'Content-Type: application/json' -b 'better-auth.session_token=demo-session-token-244' -d '{"role": "admin"}'
```

```output
HTTP 200
```

The request succeeded (HTTP 200). Now read the **stored** role straight from Mongo — the ground truth, not the API response:

```bash
uv run --project /home/frankbria/projects/auto-author/backend python /tmp/claude-1000/-home-frankbria-projects-auto-author/a1970958-55cf-4990-b245-4b0b467827bd/scratchpad/role244.py
```

```output
stored role = 'admin'
```

The victim just escalated themselves to **admin** — everything gated on `SessionRoleChecker` (e.g. `GET /users/admin/users`) is now theirs.

## The same attack on the fix branch (:8801)

Re-seed the user back to `role: user`, then fire the identical request at the branch.

```bash
uv run --project /home/frankbria/projects/auto-author/backend python /tmp/claude-1000/-home-frankbria-projects-auto-author/a1970958-55cf-4990-b245-4b0b467827bd/scratchpad/seed244.py
```

```output
Seeded DB=auto_author_demo244 user auth_id=demo-victim-244 role=user
```

```bash
curl -s -m8 -w '\nHTTP %{http_code}\n' -X PATCH http://127.0.0.1:8801/api/v1/users/me -H 'Content-Type: application/json' -b 'better-auth.session_token=demo-session-token-244' -d '{"role": "admin"}'
```

```output
{"detail":"Validation error","errors":[{"type":"extra_forbidden","loc":["body","role"],"msg":"Extra inputs are not permitted","input":"admin"}],"error_summary":"body -> role: Extra inputs are not permitted"}
HTTP 422
```

The branch rejects the request with **HTTP 422** — `UserUpdate` is now `extra=\"forbid\"`, so `role` (an undeclared, privileged key) is refused at the validation boundary before any `$set` runs. Confirm the stored role is untouched:

```bash
uv run --project /home/frankbria/projects/auto-author/backend python /tmp/claude-1000/-home-frankbria-projects-auto-author/a1970958-55cf-4990-b245-4b0b467827bd/scratchpad/role244.py
```

```output
stored role = 'user'
```

`extra=\"forbid\"` is strict, so the last thing to prove is that a **normal** profile update still works on the branch — the declared fields round-trip, only the privileged/unknown keys are refused:

```bash
curl -s -m8 -X PATCH http://127.0.0.1:8801/api/v1/users/me -H 'Content-Type: application/json' -b 'better-auth.session_token=demo-session-token-244' -d '{"first_name": "Ada", "bio": "Mathematician"}' | jq '{first_name, bio, role}'
```

```output
{
  "first_name": "Ada",
  "bio": "Mathematician",
  "role": "user"
}
```

## Verdict

| | `main` (:8802) | `fix/244` (:8801) |
|---|---|---|
| `PATCH /users/me {\"role\":\"admin\"}` | **200 OK** | **422 rejected** |
| Stored role after | **`admin`** ⚠️ escalated | **`user`** ✅ unchanged |
| Normal profile edit | works | works (declared fields round-trip) |

The privilege-escalation path is closed at the schema boundary. Because the fix is `extra=\"forbid\"` rather than a one-field strip, the *same* 422 now guards every other privileged field (`plan`, `is_active`, `stripe_*`, `book_ids`, `auth_id`) — pinned by the parameterized regression tests.
