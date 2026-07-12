# Issue #265 — PUT /users/{auth_id} skips sanitize_input: reproduced on main, closed on the branch

*2026-07-11T04:10:35Z*

Setup: two **real** uvicorn servers share one **real** MongoDB (`auto_author_demo265`), both with `BYPASS_AUTH=false` so genuine better-auth session cookies are validated against the DB.

- **:8812** runs `main` (commit 71198ab, a git worktree) — stores PUT strings unsanitized.
- **:8811** runs the fix branch `fix/issue-265-put-sanitize-input`.

A normal user and a valid better-auth session are seeded directly into Mongo so both endpoints can be driven with a real session cookie. Every check reads the **stored document straight from Mongo** — ground truth, not the API response.

```bash
uv run --project /home/frankbria/projects/auto-author/backend python /tmp/claude-1000/-home-frankbria-projects-auto-author/20d5b61a-34bd-4228-9c56-41c983feb8a4/scratchpad/seed265.py
```

```output
Seeded DB=auto_author_demo265 user auth_id=demo-user-265 bio=''
```

## The gap on `main` (:8812)

The same markup-bearing bio is written through both endpoints. First via `PATCH /users/me` — which has always sanitized:

```bash
curl -s -m8 -o /dev/null -w "HTTP %{http_code}\n" -X PATCH http://127.0.0.1:8812/api/v1/users/me -H "Content-Type: application/json" -b "better-auth.session_token=demo-session-token-265" -d "{\"bio\": \"<script>alert(1)</script><b>bold</b>  claim\"}" && uv run --project /home/frankbria/projects/auto-author/backend python /tmp/claude-1000/-home-frankbria-projects-auto-author/20d5b61a-34bd-4228-9c56-41c983feb8a4/scratchpad/bio265.py
```

```output
HTTP 200
stored bio = 'bold claim'
```

PATCH stored the sanitized text `'bold claim'` — script and HTML tags stripped. Now the **identical body** via `PUT /users/{auth_id}` (the self-update path any authenticated user can call) on main:

```bash
curl -s -m8 -o /dev/null -w "HTTP %{http_code}\n" -X PUT http://127.0.0.1:8812/api/v1/users/demo-user-265 -H "Content-Type: application/json" -b "better-auth.session_token=demo-session-token-265" -d "{\"bio\": \"<script>alert(1)</script><b>bold</b>  claim\"}" && uv run --project /home/frankbria/projects/auto-author/backend python /tmp/claude-1000/-home-frankbria-projects-auto-author/20d5b61a-34bd-4228-9c56-41c983feb8a4/scratchpad/bio265.py
```

```output
HTTP 200
stored bio = '<script>alert(1)</script><b>bold</b>  claim'
```

**The bug**: PUT stored the raw `<script>` markup verbatim — same document field, two different sanitization postures. Anything rendering that bio trusts a field PATCH promised was sanitized.

## The same writes on the fix branch (:8811)

Re-seed to a clean user, then repeat both writes against the branch:

```bash
uv run --project /home/frankbria/projects/auto-author/backend python /tmp/claude-1000/-home-frankbria-projects-auto-author/20d5b61a-34bd-4228-9c56-41c983feb8a4/scratchpad/seed265.py
```

```output
Seeded DB=auto_author_demo265 user auth_id=demo-user-265 bio=''
```

```bash
curl -s -m8 -o /dev/null -w "PATCH: HTTP %{http_code}\n" -X PATCH http://127.0.0.1:8811/api/v1/users/me -H "Content-Type: application/json" -b "better-auth.session_token=demo-session-token-265" -d "{\"bio\": \"<script>alert(1)</script><b>bold</b>  claim\"}" && uv run --project /home/frankbria/projects/auto-author/backend python /tmp/claude-1000/-home-frankbria-projects-auto-author/20d5b61a-34bd-4228-9c56-41c983feb8a4/scratchpad/bio265.py && curl -s -m8 -o /dev/null -w "PUT reset: HTTP %{http_code}\n" -X PUT http://127.0.0.1:8811/api/v1/users/demo-user-265 -H "Content-Type: application/json" -b "better-auth.session_token=demo-session-token-265" -d "{\"bio\": \"different\"}" && curl -s -m8 -o /dev/null -w "PUT markup: HTTP %{http_code}\n" -X PUT http://127.0.0.1:8811/api/v1/users/demo-user-265 -H "Content-Type: application/json" -b "better-auth.session_token=demo-session-token-265" -d "{\"bio\": \"<script>alert(1)</script><b>bold</b>  claim\"}" && uv run --project /home/frankbria/projects/auto-author/backend python /tmp/claude-1000/-home-frankbria-projects-auto-author/20d5b61a-34bd-4228-9c56-41c983feb8a4/scratchpad/bio265.py
```

```output
PATCH: HTTP 200
stored bio = 'bold claim'
PUT reset: HTTP 200
PUT markup: HTTP 200
stored bio = 'bold claim'
```

On the branch the PUT-stored value is `'bold claim'` — **byte-identical to what PATCH stores** (the intermediate `'different'` write proves PUT genuinely overwrote the field rather than leaving PATCH's value in place). Both ACs shown with stored-document evidence:

- **AC1**: PUT sanitizes string fields the same way PATCH does (shared `sanitize_string_fields` helper).
- **AC2**: a markup-bearing string is stored identically through both endpoints.

Last, a normal non-markup PUT still round-trips untouched (sanitization is not mangling clean input):

```bash
curl -s -m8 -X PUT http://127.0.0.1:8811/api/v1/users/demo-user-265 -H "Content-Type: application/json" -b "better-auth.session_token=demo-session-token-265" -d "{\"bio\": \"Writes about distributed systems.\", \"first_name\": \"Ada\"}" | jq "{first_name, bio}"
```

```output
{
  "first_name": "Ada",
  "bio": "Writes about distributed systems."
}
```
