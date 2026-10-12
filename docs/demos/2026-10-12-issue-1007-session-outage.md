# A session that cannot be checked is our outage, not a signed-out user (#1007)

*2026-10-12T22:37:39Z by Showboat 0.6.1*
<!-- showboat-id: 3fb924f5-9c61-4e7e-99be-002f24b7d70d -->

When the database was away, a signed-in request waited for the driver to give up and was then answered 401 "Please sign in", the same as for a session that does not exist. The frontend ends the session in the browser on a 401 from the API, so a database blip logged out everyone who made a request during it. This demo runs the real backend from main and from this branch against a database of its own, with one signed-in user, and stops and starts that database.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo1007/env.sh; echo "main:   $(git -C $MAIN log --oneline -1 | cut -c1-7)"; echo "branch: $(git -C $WT rev-parse --abbrev-ref HEAD)"
```

```output
main:   4cfefb7
branch: feature/issue-1007-session-outage
```

Before. With the database stopped the user waits thirty seconds and is told to sign in.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo1007/env.sh; story $MAIN; stop
```

```output
the database is up      : 200 after about 0 seconds | []
the database is stopped : 401 after about 30 seconds | {"detail":"Not authenticated. Please sign in."}
and again               : 401 after about 30 seconds | {"detail":"Not authenticated. Please sign in."}
the database is back    : 200 after about 0 seconds | []
```

After. The same request is answered in five seconds with a 503 that says to try again and when. When the database is back the same cookie works: nobody was signed out.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo1007/env.sh; story $WT; stop
```

```output
the database is up      : 200 after about 0 seconds | []
the database is stopped : 503 after about 5 seconds | {"detail":"The service is temporarily unavailable. Please try again in a moment."} | retry-after: 5
and again               : 503 after about 5 seconds | {"detail":"The service is temporarily unavailable. Please try again in a moment."} | retry-after: 5
the database is back    : 200 after about 0 seconds | []
```

A request with a cookie for a session that does not exist is still asked to sign in, with the database up.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo1007/env.sh; database; backend $WT; COOKIE="better-auth.session_token=$(python3 $D/cookie.py NO-SUCH-SESSION $AUTH_SECRET)"; ask 'a session that is not there'; stop
```

```output
a session that is not there: 401 after about 0 seconds | {"detail":"Not authenticated. Please sign in."}
```

The same behaviour as tests: the lookups against a driver whose server is not there, the route, the single report, and the frontend leaving the session alone on a 503.

```bash
cd /home/frankbria/projects/worktrees/issue-1007-session-outage/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo1007 uv run pytest tests/test_core/test_session_store_unavailable.py -q -p no:cacheprovider --no-cov 2>&1 | tail -1 | sed -E 's/ in [0-9.]*s//; s/, [0-9]+ warnings?//'; cd /home/frankbria/projects/worktrees/issue-1007-session-outage/frontend && npx jest src/lib/api/__tests__/unauthorized.test.ts 2>&1 | grep -E '^Tests:' | sed -E 's/ +/ /g'
```

```output
========================= 9 passed =========================
Tests: 12 passed, 12 total
```
