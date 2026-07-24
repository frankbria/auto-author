# Demo — #333: `/health` verifies Mongo + required secrets so broken releases fail the deploy gate

**Issue (P1.1):** `/health` returned a static `{"status":"healthy"}` with zero dependency
checks, so the deploy gate `curl -f .../api/v1/health` only proved uvicorn accepts a
socket. A release with a wrong `MONGODB_URI`, un-allowlisted Atlas IP, or a missing
`OPENAI_API_KEY`/`BETTER_AUTH_SECRET` passed the health check and was promoted while
every real request 500s.

All output below is real, captured from live uvicorn servers (real local Mongo) and the
endpoint test harness.

---

## The money shot — same config, opposite outcome (AC2 + AC3)

Two servers, **byte-identical env** (`ENVIRONMENT=production`, a strong
`BETTER_AUTH_SECRET`, Mongo up, but `OPENAI_API_KEY` never wired in — only the CI
placeholder `test-key`): `main` (pristine worktree) vs this branch.

```
[MAIN-bug  :8405] HTTP=200  curl-f-exit=0   body={"status":"healthy"}
[BRANCH-fix :8404] HTTP=503  curl-f-exit=22  body={"status":"unhealthy","checks":{"mongodb":"ok","config":"missing: OPENAI_API_KEY"}}
```

- **main**: static `200 healthy`, `curl -f` exits `0` → the deploy gate **promotes a broken release**. This is the bug.
- **branch**: `503`, body **names the failing component** (`config: missing: OPENAI_API_KEY`), `curl -f` exits `22` → the deploy gate **blocks the release** (AC3).
- `checks.mongodb: "ok"` proves the **real** `db.command("ping")` ran and succeeded — the branch pings Mongo *and* checks the keys (AC1).

The deploy workflow needed **no change**: `deploy-staging.yml` already runs
`curl -f http://localhost:8000/api/v1/health` in a retry-then-`exit 1` loop. The gate was
always correct — only the probe lied.

---

## AC1 — healthy release still passes (branch, good Mongo, secrets present)

```
$ curl -s http://127.0.0.1:8401/api/v1/health
{"status":"healthy","checks":{"mongodb":"ok","config":"ok"}}
HTTP 200
$ curl -f ... ; echo exit=$?
exit=0            # gate passes a HEALTHY release
```

A real Mongo ping (`mongodb: ok`) and configured secrets (`config: ok`) → `200`. No
false-fail; CI (which uses the placeholder secrets in a non-production env) stays green.

## AC2 — Mongo unreachable → 503 naming the component

Ping raises (wrong URI / un-allowlisted Atlas IP / Mongo down):

```
HTTP 503 {'status': 'unhealthy', 'checks': {'mongodb': 'error: Exception', 'config': 'ok'}}
```

The bounded ping (`asyncio.wait_for`, 5s) means a broken/unreachable Mongo fails the probe
*fast* instead of hanging on the app client's 30s server-selection timeout — the deploy
gate retries with short sleeps and must get a prompt 503.

---

## Coverage

| Acceptance criterion | Evidence |
|---|---|
| `/health` pings Mongo (`db.command('ping')`) + asserts required keys present | branch `:8401` → `mongodb: ok, config: ok`; `:8404` → `mongodb: ok` (real ping) + `config` catches the missing key |
| Returns 503 with the failing component | `:8404` → `503 … config: missing: OPENAI_API_KEY`; Mongo-down → `503 … mongodb: error: …` |
| Deploy `curl -f` fails a broken release | main `curl -f` exit `0` (promotes broken) vs branch exit `22` (blocks) — same env |
