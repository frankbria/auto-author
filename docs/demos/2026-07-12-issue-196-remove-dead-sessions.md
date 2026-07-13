# Issue #196: dead Session Management subsystem removed (PR #282)

*2026-07-13T01:57:41Z*

The advertised "Session Management" security feature (30-min idle timeout, 12-hr absolute timeout, expiry warnings, suspicious-activity detection) was dead code: `SessionMiddleware` only acted when `request.state.user` was set, but nothing in the app ever set it — auth is a FastAPI dependency that returns the user directly. This demo runs TWO real uvicorn servers against the same local MongoDB with the SAME genuine better-auth session: **main** (pre-fix, port 8300, worktree at commit 2e93c38) vs **branch** `fix/196-remove-dead-session-subsystem` (port 8301). Both servers were started with `BYPASS_AUTH=false`.

Both servers are healthy, and the seeded better-auth session authenticates on BOTH — `/users/me` returns 200. So any difference on `/sessions/*` below is the route change, not an auth artifact.

```bash
T=$(cat /tmp/claude-1000/-home-frankbria-projects-auto-author/d65311f9-b04b-4f1f-8ffa-2b9d2c3409c1/scratchpad/demo196.token)
curl -s -o /dev/null -w "main   :8300 /api/v1/health   -> %{http_code}\n" http://127.0.0.1:8300/api/v1/health
curl -s -o /dev/null -w "branch :8301 /api/v1/health   -> %{http_code}\n" http://127.0.0.1:8301/api/v1/health
curl -s -o /dev/null -w "main   :8300 /api/v1/users/me -> %{http_code} (authenticated)\n" -H "Cookie: better-auth.session_token=$T" http://127.0.0.1:8300/api/v1/users/me
curl -s -o /dev/null -w "branch :8301 /api/v1/users/me -> %{http_code} (authenticated)\n" -H "Cookie: better-auth.session_token=$T" http://127.0.0.1:8301/api/v1/users/me
```

```output
main   :8300 /api/v1/health   -> 200
branch :8301 /api/v1/health   -> 200
main   :8300 /api/v1/users/me -> 200 (authenticated)
branch :8301 /api/v1/users/me -> 200 (authenticated)
```

**MAIN (the bug).** The same authenticated user asks the "session management" API about their session. `/sessions/current` says there is NO active session — despite the valid better-auth session that just authenticated the request — because the middleware that was supposed to create tracking sessions never fired. `/sessions/list` "works" but is permanently empty. The OpenAPI schema still advertises 6 session endpoints.

```bash
T=$(cat /tmp/claude-1000/-home-frankbria-projects-auto-author/d65311f9-b04b-4f1f-8ffa-2b9d2c3409c1/scratchpad/demo196.token)
echo "--- GET /api/v1/sessions/current (authenticated) ---"
curl -s -w "\nHTTP %{http_code}\n" -H "Cookie: better-auth.session_token=$T" http://127.0.0.1:8300/api/v1/sessions/current
echo "--- GET /api/v1/sessions/list (authenticated) ---"
curl -s -w "\nHTTP %{http_code}\n" -H "Cookie: better-auth.session_token=$T" http://127.0.0.1:8300/api/v1/sessions/list
echo "--- advertised session endpoints in OpenAPI ---"
curl -s http://127.0.0.1:8300/openapi.json | python3 -c "import json,sys; print(*[p for p in json.load(sys.stdin)[\"paths\"] if \"/sessions\" in p], sep=\"\n\")"
```

```output
--- GET /api/v1/sessions/current (authenticated) ---
{"detail":"No active session found"}
HTTP 404
--- GET /api/v1/sessions/list (authenticated) ---
[]
HTTP 200
--- advertised session endpoints in OpenAPI ---
/api/v1/sessions/current
/api/v1/sessions/refresh
/api/v1/sessions/logout
/api/v1/sessions/logout-all
/api/v1/sessions/list
/api/v1/sessions/{session_id}
```

**BRANCH (the fix).** Same authenticated requests: the routes are gone entirely — plain route-level 404 ("Not Found"), and the OpenAPI schema advertises zero session endpoints. The middleware stack no longer contains SessionMiddleware on the branch.

```bash
T=$(cat /tmp/claude-1000/-home-frankbria-projects-auto-author/d65311f9-b04b-4f1f-8ffa-2b9d2c3409c1/scratchpad/demo196.token)
echo "--- GET /api/v1/sessions/current (authenticated) ---"
curl -s -w "\nHTTP %{http_code}\n" -H "Cookie: better-auth.session_token=$T" http://127.0.0.1:8301/api/v1/sessions/current
echo "--- GET /api/v1/sessions/list (authenticated) ---"
curl -s -w "\nHTTP %{http_code}\n" -H "Cookie: better-auth.session_token=$T" http://127.0.0.1:8301/api/v1/sessions/list
echo "--- session endpoints in OpenAPI ---"
curl -s http://127.0.0.1:8301/openapi.json | python3 -c "import json,sys; ps=[p for p in json.load(sys.stdin)[\"paths\"] if \"/sessions\" in p]; print(ps if ps else \"(none)\")"
```

```output
--- GET /api/v1/sessions/current (authenticated) ---
{"detail":"Not Found"}
HTTP 404
--- GET /api/v1/sessions/list (authenticated) ---
{"detail":"Not Found"}
HTTP 404
--- session endpoints in OpenAPI ---
(none)
```

```bash
echo "--- main middleware stack ---"
cd /tmp/claude-1000/-home-frankbria-projects-auto-author/d65311f9-b04b-4f1f-8ffa-2b9d2c3409c1/scratchpad/aa-main-196/backend && uv run python -c "from app.main import app; print([m.cls.__name__ for m in app.user_middleware])" 2>/dev/null | tail -1
echo "--- branch middleware stack ---"
cd /home/frankbria/projects/auto-author/backend && uv run python -c "from app.main import app; print([m.cls.__name__ for m in app.user_middleware])" 2>/dev/null | tail -1
```

```output
--- main middleware stack ---
['SessionMiddleware', 'RequestValidationMiddleware', 'CORSMiddleware']
--- branch middleware stack ---
['RequestValidationMiddleware', 'CORSMiddleware']
```

**Frontend + docs.** The never-mounted polling hook and warning component are deleted; every remaining `useSession` import resolves to the better-auth re-export (the live session feature — `ActiveSessionsList` in Settings → Security — is untouched). CLAUDE.md no longer lists Session Management as Production Ready.

```bash
cd /home/frankbria/projects/auto-author
echo "--- legacy frontend files (branch) ---"
ls frontend/src/hooks/useSession.ts frontend/src/components/session/SessionWarning.tsx 2>&1
echo "--- same files exist on main ---"
git -C /tmp/claude-1000/-home-frankbria-projects-auto-author/d65311f9-b04b-4f1f-8ffa-2b9d2c3409c1/scratchpad/aa-main-196 ls-files | grep -E "hooks/useSession.ts|SessionWarning"
echo "--- remaining useSession imports all resolve to better-auth ---"
grep -rh "import.*useSession" frontend/src --include="*.tsx" --include="*.ts" | grep -v "auth-client\|better-auth" | wc -l
echo "--- Production Ready list no longer advertises Session Management ---"
sed -n "/### ✅ Production Ready/,/^$/p" CLAUDE.md | head -5
```

```output
--- legacy frontend files (branch) ---
ls: cannot access 'frontend/src/hooks/useSession.ts': No such file or directory
ls: cannot access 'frontend/src/components/session/SessionWarning.tsx': No such file or directory
--- same files exist on main ---
frontend/src/components/session/SessionWarning.tsx
frontend/src/hooks/useSession.ts
--- remaining useSession imports all resolve to better-auth ---
0
--- Production Ready list no longer advertises Session Management ---
### ✅ Production Ready
- User authentication (better-auth with HS256 JWT verification; session list/revoke via better-auth native APIs in Settings → Security)
- Book CRUD operations with metadata
- **Book Deletion UI** (Type-to-confirm with data loss warnings)
- TOC generation with AI wizard
```

**Regression tests** pin the removal. `test_sessions_list_route_is_gone` was RED-verified against the old code (main returned HTTP 200 for `/sessions/list`, as shown above); both tests are green on the branch.

```bash
cd /home/frankbria/projects/auto-author/backend && BYPASS_AUTH=false uv run pytest tests/test_api/test_routes/test_sessions_removed.py -q 2>&1 | tail -2 | sed "s/ in [0-9.]*s//"
```

```output

============================== 2 passed ===============================
```

**Conclusion.** The AC removal branch is fully delivered: `/sessions/*` router gone (route-level 404 + zero OpenAPI paths), SessionMiddleware gone from the stack, frontend polling deleted (all remaining `useSession` = better-auth), and the feature is no longer advertised. Full suites: backend 1111 passed / 91.81% cov; frontend 115 suites / 2109 passed.
