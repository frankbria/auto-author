# Issue #814: the API knows it is served over https, both hosts send HSTS, and the frontend does not name its framework

*2026-10-12T23:54:28Z by Showboat 0.6.1*
<!-- showboat-id: 1af15897-2187-4705-a7bf-fb48771773e3 -->

Three acceptance criteria: the redirect the API builds is https; HSTS is sent by both hosts; the frontend sends no `X-Powered-By`.

## Before: staging, which runs main

The API is asked over https for `/api/v1/books` and redirects to the same address with a trailing slash, over **http**. No `strict-transport-security` on either host. The frontend says what it is built with.

```bash
curl -s -o /dev/null -D - --max-time 20 https://api.dev.autoauthor.app/api/v1/books | grep -i -E "^HTTP|^location|^strict-transport|^x-powered-by" | tr -d "\r"
```

```output
HTTP/2 307 
location: http://api.dev.autoauthor.app/api/v1/books/
```

```bash
curl -s -o /dev/null -D - --max-time 20 https://dev.autoauthor.app/ | grep -i -E "^HTTP|^location|^strict-transport|^x-powered-by" | tr -d "\r"
```

```output
HTTP/2 200 
x-powered-by: Next.js
```

## Why: uvicorn already reads the headers, from loopback only

The issue asks for `--proxy-headers`. That is already the default in the image that is running:

```bash
docker run --rm --entrypoint uvicorn ghcr.io/frankbria/auto-author-backend:sha-7a3a2de --help | grep -A 3 -e '--proxy-headers' -e '--forwarded-allow-ips' | cut -c1-110
```

```output
  --proxy-headers / --no-proxy-headers
                                  Enable/Disable X-Forwarded-Proto,
                                  X-Forwarded-For to populate url scheme and
                                  remote address info.
--
  --forwarded-allow-ips TEXT      Comma separated list of IP Addresses, IP
                                  Networks, or literals (e.g. UNIX Socket
                                  path) to trust with proxy headers. Defaults
                                  to the $FORWARDED_ALLOW_IPS environment
```

The image built from main, run by main`s `docker-compose.yml` with one local overlay (a scratch port, a database beside it, no `.env` file). `ask.sh` sends what nginx sends for a caller at `198.51.100.9` who wrote an `X-Forwarded-For: 203.0.113.7` of their own, then prints the client the backend logged.

The backend sees the request come from the Docker network`s gateway, which is not loopback, so it does not believe the headers: the redirect is http and the logged client is the gateway.

```bash
cat /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo814/ask.sh | tail -2
```

```output
curl -s -o /dev/null -D - --max-time 10 -H "Host: api.example.test" -H "X-Forwarded-Proto: https" -H "X-Forwarded-For: 203.0.113.7, 198.51.100.9" http://127.0.0.1:18814/api/v1/books | grep -i -E "^HTTP|^location|^strict-transport" | tr -d "\r"
docker logs aa814-backend-1 2>&1 | grep -o "Request started: GET /api/v1/books from [0-9.]*" | tail -1
```

```bash
cd /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo814 && ./up.sh compose-main.yml ghcr.io/frankbria/auto-author-backend:sha-7a3a2de && ./ask.sh
```

```output
FORWARDED_ALLOW_IPS in the container: (not set)
HTTP/1.1 307 Temporary Redirect
location: http://api.example.test/api/v1/books/
Request started: GET /api/v1/books from 172.22.0.1
```

## After: the image built from this branch, run by this branch`s `docker-compose.yml`

The same overlay and the same request. The compose file gives uvicorn the ranges Docker hands out to its networks. The redirect is **https**, the answer carries HSTS, and the logged client is the address nginx added, not the one the caller wrote and not the gateway.

```bash
cd /home/frankbria/projects/worktrees/issue-814-proxy-headers && git diff main -- docker-compose.yml | grep '^[+-]' | grep -v '^+++\|^---'
```

```output
+      # Whose X-Forwarded-Proto and X-Forwarded-For uvicorn believes (#814). Its
+      # default is loopback, but nginx on the host reaches this container as the
+      # Docker network's gateway, so the API thought it was served over http and
+      # redirected there. These are the ranges Docker gives its networks. Not
+      # "*": that takes the first X-Forwarded-For address, which the caller
+      # writes; with a list uvicorn takes the last one that is not a proxy.
+      FORWARDED_ALLOW_IPS: "172.16.0.0/12,192.168.0.0/16"
```

```bash
cd /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo814 && ./up.sh compose-branch.yml aa814-backend && ./ask.sh
```

```output
FORWARDED_ALLOW_IPS in the container: 172.16.0.0/12,192.168.0.0/16
HTTP/1.1 307 Temporary Redirect
location: https://api.example.test/api/v1/books/
strict-transport-security: max-age=31536000
Request started: GET /api/v1/books from 198.51.100.9
```

## After: the frontend from this branch

`next dev` on a scratch port. HSTS is there and `X-Powered-By` is not (the grep asks for both).

```bash
curl -s -o /dev/null -D - --max-time 30 http://127.0.0.1:13814/ | grep -i -E "^HTTP|^location|^strict-transport|^x-powered-by" | tr -d "\r"
```

```output
HTTP/1.1 200 OK
Strict-Transport-Security: max-age=31536000
```

## Tests

The backend test runs uvicorn`s own middleware with the list read out of `docker-compose.yml`, in front of the real app: a request from a Docker gateway in each range is redirected to https; the client is the address nginx added; a peer that is not the proxy is not believed; the answer carries HSTS. The frontend test reads `next.config.ts`.

```bash
cd /home/frankbria/projects/worktrees/issue-814-proxy-headers/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo814 uv run pytest tests/test_api/test_proxy_headers.py -q -p no:cacheprovider --no-cov 2>&1 | tail -1
```

```output
============================== 7 passed in 0.10s ===============================
```

```bash
cd /home/frankbria/projects/worktrees/issue-814-proxy-headers/frontend && npx jest src/__tests__/nextConfigHeaders.test.ts 2>&1 | grep -E 'Tests:'
```

```output
Tests:       3 passed, 3 total
```

## What this cannot show before it is deployed

The first criterion is about staging itself: nginx there has to send `X-Forwarded-Proto`, and Docker there has to use its default address ranges. Both are checked after the deploy with the first command of this document, and the result is posted on the pull request.
