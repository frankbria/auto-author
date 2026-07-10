# Issue #189: app processes bind 127.0.0.1 behind nginx on the shared staging VPS

*2026-07-10T19:07:34Z*

Before the fix (PR #268), PM2 started uvicorn with --host 0.0.0.0 and Next.js with its default wildcard bind on the shared staging VPS. BEFORE state, live on the server: both apps listen on all interfaces.

```bash
ssh staging 'ss -tln | grep -E ":8000|:3002"; pm2 describe auto-author-backend | grep "script args"'
```

```output
LISTEN 0      2048                       0.0.0.0:8000       0.0.0.0:*          
LISTEN 0      511                              *:3002             *:*          
│ script args       │ app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips=127.0.0.1 │
```

The host firewall (ufw, default-deny) already drops external 8000/3002 — the AC "OR" branch — but nothing in the repo documented it. From an off-box machine, direct port access times out while the nginx-proxied HTTPS endpoints serve normally:

```bash
curl -sm 5 http://195.35.14.177:8000/api/v1/health -o /dev/null -w "direct 8000: %{http_code}\n" || echo "direct 8000: TIMEOUT/UNREACHABLE"; curl -sm 5 http://195.35.14.177:3002 -o /dev/null -w "direct 3002: %{http_code}\n" || echo "direct 3002: TIMEOUT/UNREACHABLE"; curl -sm 10 https://api.dev.autoauthor.app/api/v1/health -o /dev/null -w "via nginx api: %{http_code}\n"; curl -sm 10 https://dev.autoauthor.app -o /dev/null -w "via nginx app: %{http_code}\n"
```

```output
direct 8000: 000
direct 8000: TIMEOUT/UNREACHABLE
direct 3002: 000
direct 3002: TIMEOUT/UNREACHABLE
via nginx api: 200
via nginx app: 200
```

Step 1 — pin nginx to explicit 127.0.0.1 upstreams. The server /etc/hosts maps localhost to both 127.0.0.1 and ::1; with a loopback-only IPv4 bind, "proxy_pass http://localhost:..." would try ::1 first and rely on passive failover. Explicit IPv4 removes the retry noise:

```bash
ssh staging 'sed -i "s|proxy_pass http://localhost:8000|proxy_pass http://127.0.0.1:8000|" /etc/nginx/sites-available/api.dev.autoauthor.app; sed -i "s|proxy_pass http://localhost:3002|proxy_pass http://127.0.0.1:3002|" /etc/nginx/sites-available/dev.autoauthor.app; grep -Hn proxy_pass /etc/nginx/sites-available/api.dev.autoauthor.app /etc/nginx/sites-available/dev.autoauthor.app; nginx -t && systemctl reload nginx && echo "nginx reloaded"'
```

```output
/etc/nginx/sites-available/api.dev.autoauthor.app:5:        proxy_pass http://127.0.0.1:8000;
/etc/nginx/sites-available/dev.autoauthor.app:5:        proxy_pass http://127.0.0.1:3002;
2026/07/10 19:08:19 [warn] 977368#977368: "ssl_stapling" ignored, no OCSP responder URL in the certificate "/etc/letsencrypt/live/dev.podcaststudiohub.me/fullchain.pem"
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
nginx reloaded
```

Step 2 — apply the exact PR #268 template change to the deployed ecosystem.config.js (backend --host 127.0.0.1; frontend next start -H 127.0.0.1) and restart PM2 with delete+start (args changes need a fresh start, same as the deploy workflow):

```bash
ssh staging 'cd /opt/auto-author/current && sed -i "s|--host 0.0.0.0|--host 127.0.0.1|; s|args: .start.,|args: \"start -- -H 127.0.0.1\",|" ecosystem.config.js && grep -n "args:" ecosystem.config.js && pm2 delete auto-author-backend auto-author-frontend >/dev/null 2>&1; pm2 start ecosystem.config.js >/dev/null 2>&1 && pm2 save >/dev/null 2>&1 && echo "pm2 restarted"'
```

```output
13:      args: 'app.main:app --host 127.0.0.1 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips=127.0.0.1',
30:      args: "start -- -H 127.0.0.1",
pm2 restarted
```

Step 3 — AFTER state. Both apps now listen on 127.0.0.1 only (waiting for Next.js to finish booting first):

```bash
ssh staging 'ss -tln | grep -E ":8000|:3002"; pm2 ls | grep auto-author'
```

```output
LISTEN 0      511                      127.0.0.1:3002       0.0.0.0:*          
LISTEN 0      2048                     127.0.0.1:8000       0.0.0.0:*          
│ 46 │ auto-author-backend           │ default     │ 1.0.0   │ fork    │ 977510   │ 35s    │ 0    │ online    │ 0%       │ 97.9mb   │ root     │ disabled │
│ 47 │ auto-author-frontend          │ default     │ N/A     │ fork    │ 977511   │ 35s    │ 0    │ online    │ 0%       │ 51.6mb   │ root     │ disabled │
```

The app still works end-to-end through nginx (TLS + real response bodies), deploy health checks on localhost keep working, and direct external port access remains dead:

```bash
echo "--- via nginx (off-box) ---"; curl -sm 10 https://api.dev.autoauthor.app/api/v1/health; echo; curl -sm 15 https://dev.autoauthor.app -o /dev/null -w "frontend via nginx: %{http_code}\n"; echo "--- deploy health checks (on-box, localhost) ---"; ssh staging 'curl -sf http://localhost:8000/api/v1/health >/dev/null && echo "localhost:8000 health OK"; curl -sf http://localhost:3002 -o /dev/null && echo "localhost:3002 OK"'; echo "--- direct external (must stay unreachable) ---"; curl -sm 5 http://195.35.14.177:8000/api/v1/health -o /dev/null -w "direct 8000: %{http_code}\n" || echo "direct 8000: TIMEOUT/UNREACHABLE"; curl -sm 5 http://195.35.14.177:3002 -o /dev/null -w "direct 3002: %{http_code}\n" || echo "direct 3002: TIMEOUT/UNREACHABLE"
```

```output
--- via nginx (off-box) ---
{"status":"healthy"}
frontend via nginx: 200
--- deploy health checks (on-box, localhost) ---
localhost:8000 health OK
localhost:3002 OK
--- direct external (must stay unreachable) ---
direct 8000: 000
direct 8000: TIMEOUT/UNREACHABLE
direct 3002: 000
direct 3002: TIMEOUT/UNREACHABLE
```

AC coverage: (1) backend binds 127.0.0.1 behind nginx — proven by ss + working https round trip; the ecosystem template change in PR #268 makes every future deploy inherit it (the on-server config was patched identically so the fix is live now, not just on next deploy). (2) The host firewall dropping external 8000/3002 is now documented in docs/STAGING-DEPLOYMENT.md and verified above (ufw default-deny, only 22/80/443 open; direct curls time out). Frontend :3002 got the same loopback treatment via next start -H 127.0.0.1. nginx now proxies to explicit 127.0.0.1 upstreams to avoid ::1 failover.

Note on showboat verify: this demo records a one-way state transition (0.0.0.0 → 127.0.0.1) applied live to the server, so the BEFORE blocks intentionally do not reproduce on re-run — the diff verify reports on block 2 (expected 0.0.0.0, actual 127.0.0.1) is the fix holding. All mutation steps are idempotent; the AFTER evidence blocks reproduce modulo PIDs/uptime.
