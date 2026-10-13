# Issue #815: a deployed API serves no documentation, and its policy drops what only the Swagger page needed

*2026-10-13T00:44:08Z by Showboat 0.6.1*
<!-- showboat-id: 541e5f5f-2d01-4351-ae0c-c50f6c76b9d6 -->

Three acceptance criteria: `/docs` and `/openapi.json` answer 404 when the environment is a deployed one; the jsdelivr and `unsafe-inline` allowances are gone from the policy there; local and development behaviour is unchanged.

`ask.sh` asks for each documentation route and for the liveness route, prints the status of each, and prints the `Content-Security-Policy` the API sends.

```bash
cat /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo815/ask.sh | tail -5
```

```output
BASE=${1:-http://127.0.0.1:18815}
for path in /docs /redoc /openapi.json /docs/oauth2-redirect /api/v1/health/live; do
  printf '%-24s %s\n' "$path" "$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$BASE$path")"
done
curl -s -o /dev/null -D - --max-time 20 "$BASE/api/v1/health/live" | grep -i '^content-security-policy' | tr -d '\r'
```

## Before: staging, which runs main

All four documentation routes answer 200, and the policy allows script and style from jsdelivr and inline.

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo815/ask.sh https://api.dev.autoauthor.app
```

```output
/docs                    200
/redoc                   200
/openapi.json            200
/docs/oauth2-redirect    200
/api/v1/health/live      200
content-security-policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; connect-src 'self'; frame-src 'self'; font-src 'self' data: https://r2cdn.perplexity.ai;
```

## Before, locally: the image built from main, started as staging

The repository`s `docker-compose.yml` with one local overlay (a scratch port, a database beside it, no `.env` file). The same as staging.

```bash
cd /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo815 && ./up.sh ghcr.io/frankbria/auto-author-backend:sha-e73acc6 staging && ./ask.sh
```

```output
ENVIRONMENT in the container: staging
/docs                    200
/redoc                   200
/openapi.json            200
/docs/oauth2-redirect    200
/api/v1/health/live      200
content-security-policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; connect-src 'self'; frame-src 'self'; font-src 'self' data: https://r2cdn.perplexity.ai;
```

## After: the image built from this branch, started as staging

The four routes are 404. The API itself still answers. The policy is `default-src` `self` and nothing else.

```bash
cd /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo815 && ./up.sh aa815-backend staging && ./ask.sh
```

```output
ENVIRONMENT in the container: staging
/docs                    404
/redoc                   404
/openapi.json            404
/docs/oauth2-redirect    404
/api/v1/health/live      200
content-security-policy: default-src 'self'
```

## After: the same image, started as development

Unchanged: the routes are there, and so is the policy the Swagger page needs.

```bash
cd /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo815 && ./up.sh aa815-backend development && ./ask.sh
```

```output
ENVIRONMENT in the container: development
/docs                    200
/redoc                   200
/openapi.json            200
/docs/oauth2-redirect    200
/api/v1/health/live      200
content-security-policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; connect-src 'self'; frame-src 'self'; font-src 'self' data: https://r2cdn.perplexity.ai;
```

## Tests

The deployed cases import the app in a fresh interpreter with `ENVIRONMENT` set to `staging` and to `production`, as a deploy does, and ask it for each route. The development case does the same, and one more asks the app the rest of the suite uses.

```bash
cd /home/frankbria/projects/worktrees/issue-815-docs-off/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo815 uv run pytest tests/test_api/test_docs_off_when_deployed.py -p no:cacheprovider --no-cov -v 2>&1 | grep -E 'PASSED|FAILED|passed|failed' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//'
```

```output
tests/test_api/test_docs_off_when_deployed.py::test_a_deployed_api_serves_no_documentation[staging] PASSED
tests/test_api/test_docs_off_when_deployed.py::test_a_deployed_api_serves_no_documentation[production] PASSED
tests/test_api/test_docs_off_when_deployed.py::test_a_deployed_api_allows_no_script_from_elsewhere_and_none_inline[staging] PASSED
tests/test_api/test_docs_off_when_deployed.py::test_a_deployed_api_allows_no_script_from_elsewhere_and_none_inline[production] PASSED
tests/test_api/test_docs_off_when_deployed.py::test_a_development_api_still_serves_its_documentation PASSED
tests/test_api/test_docs_off_when_deployed.py::test_so_does_the_app_under_test PASSED
6 passed in 5.07s
```

## What this cannot show before it is deployed

Staging itself. After the deploy the first command of this document is run again and the result is posted on the pull request.
