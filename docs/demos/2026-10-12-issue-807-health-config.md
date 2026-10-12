# In production /health fails when the box cannot store uploads, bill or report errors, and liveness has its own route (#807)

*2026-10-12T14:31:24Z by Showboat 0.6.1*
<!-- showboat-id: e7e7addc-23bf-488a-90f9-50d18b9a4931 -->

The health route is the deploy gate. It checked the database and two secrets, so a production deployment that could not store uploads, take payment or report errors passed it. This demo starts the real backend from main and from this branch as different deployments and asks each for its health. Every provider value is the word "placeholder"; nothing is contacted.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo807/env.sh; echo "main:   $(git -C $MAIN log --oneline -1 | cut -c1-7)"; echo "branch: $(git -C $WT rev-parse --abbrev-ref HEAD)"; echo "a production deployment in this demo sets: $(echo $PROD $BILLING $REPORTING | tr ' ' '\n' | cut -d= -f1 | tr '\n' ' ')"
```

```output
main:   e668511
branch: feature/issue-807-health-config
a production deployment in this demo sets: ENVIRONMENT BYPASS_AUTH E2E_ALLOW_BYPASS CLOUDINARY_CLOUD_NAME CLOUDINARY_API_KEY CLOUDINARY_API_SECRET STRIPE_SECRET_KEY STRIPE_WEBHOOK_SECRET STRIPE_PRICE_ID_PRO SENTRY_DSN 
```

Before. Main, started as production with a storage provider and nothing else: no Stripe values, no Sentry DSN. Its health is 200, with no word about either.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo807/env.sh; boot $MAIN $D/work $PROD 2>/dev/null; health | fold -s -w 150; stop 2>/dev/null
```

```output
the backend started
/api/v1/health -> HTTP 200  {"status":"healthy","checks":{"mongodb":"ok","config":"ok"}}
```

After. The same deployment on this branch is a 503 that names what is missing, by setting name. Adding the Stripe values leaves Sentry; adding the DSN makes it healthy.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo807/env.sh; boot $WT $D/work $PROD 2>/dev/null; health | fold -s -w 150; boot $WT $D/work $PROD $BILLING 2>/dev/null; health | fold -s -w 150; boot $WT $D/work $PROD $BILLING $REPORTING 2>/dev/null; health | fold -s -w 150; stop 2>/dev/null
```

```output
the backend started
/api/v1/health -> HTTP 503  {"status":"unhealthy","checks":{"mongodb":"ok","config":"ok","storage":"ok","billing":"missing: STRIPE_SECRET_KEY, 
STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_ID_PRO","error_reporting":"missing: SENTRY_DSN"}}
the backend started
/api/v1/health -> HTTP 503  {"status":"unhealthy","checks":{"mongodb":"ok","config":"ok","storage":"ok","billing":"ok","error_reporting":"missing: 
SENTRY_DSN"}}
the backend started
/api/v1/health -> HTTP 200  {"status":"healthy","checks":{"mongodb":"ok","config":"ok","storage":"ok","billing":"ok","error_reporting":"ok"}}
```

A deployment that sells nothing says so with BILLING_ENABLED=false, and billing is reported as disabled instead of missing.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo807/env.sh; boot $WT $D/work $PROD $REPORTING BILLING_ENABLED=false 2>/dev/null; health | fold -s -w 150; stop 2>/dev/null
```

```output
the backend started
/api/v1/health -> HTTP 200  {"status":"healthy","checks":{"mongodb":"ok","config":"ok","storage":"ok","billing":"disabled","error_reporting":"ok"}}
```

Storage has a guard in front of this one. Since #806 a production backend without a storage provider does not start, so its health is never asked.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo807/env.sh; boot $WT $D/work ENVIRONMENT=production BYPASS_AUTH=false E2E_ALLOW_BYPASS= $BILLING $REPORTING 2>/dev/null | fold -s -w 150; stop 2>/dev/null
```

```output
the backend did not start: RuntimeError: Application startup blocked: no upload storage is configured, so uploads would go to local disk in 
production. Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET or AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET.
```

Outside production the same gaps are reported and the answer stays 200. This is what staging will show: it keeps passing its gate, and what it has configured becomes visible from outside.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo807/env.sh; boot $WT $D/work ENVIRONMENT=staging BYPASS_AUTH=false E2E_ALLOW_BYPASS= 2>/dev/null; health | fold -s -w 150; stop 2>/dev/null
```

```output
the backend started
/api/v1/health -> HTTP 200  {"status":"healthy","checks":{"mongodb":"ok","config":"ok","storage":"missing: CLOUDINARY_* or AWS_*","billing":"missing: 
STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_ID_PRO","error_reporting":"missing: SENTRY_DSN"}}
```

Liveness. The backend is started against a database of its own, and then that database is stopped. The readiness route turns 503, as it should. The liveness route, which touches nothing, still answers 200; main has no such route. The container health check in docker-compose.yml now asks the liveness route, so a database outage no longer marks a live container unhealthy.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo807/env.sh; own_database && echo 'a database of its own is up on port 27999'; boot $WT $D/work DATABASE_URL=mongodb://127.0.0.1:27999 2>/dev/null; health health/live; database_goes_away; echo 'the database is stopped'; health | cut -c1-110; health health/live; boot $MAIN $D/work 2>/dev/null; echo 'main:'; health health/live; stop 2>/dev/null; grep -n 'health' $WT/docker-compose.yml | grep 'test:' | sed -E 's/.*(http[^,]*)..timeout.*/the compose health check asks: \1/'
```

```output
a database of its own is up on port 27999
the backend started
/api/v1/health/live -> HTTP 200  {"status":"alive"}
the database is stopped
/api/v1/health -> HTTP 503  {"status":"unhealthy","checks":{"mongodb":"error: TimeoutError","config":"ok","sto
/api/v1/health/live -> HTTP 200  {"status":"alive"}
the backend started
main:
/api/v1/health/live -> HTTP 404  {"detail":"Not Found"}
the compose health check asks: http://127.0.0.1:8000/api/v1/health/live'
```

The same behaviour as tests: every missing capability in production as its own case, the same gaps outside production (and a NODE_ENV=production left in a staging box does not make it production), the liveness route with the database unreachable, and the compose file.

```bash
cd /home/frankbria/projects/worktrees/issue-807-health-config/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo807 uv run pytest tests/test_api/test_health_configuration.py -q -p no:cacheprovider --no-cov 2>&1 | tail -1 | sed 's/ in [0-9.]*s//'
```

```output
============================== 17 passed ==============================
```
