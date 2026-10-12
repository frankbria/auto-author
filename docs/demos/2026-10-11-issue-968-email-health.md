# Issue #968: the frontend reports whether sign-up email can be sent

*2026-10-11T23:49:00Z by Showboat 0.6.1*
<!-- showboat-id: 6417bcd8-f642-4d5a-baaf-115426e28086 -->

Since #792 nobody can finish signing up without the verification email, and a missing provider is invisible to the user. This demo runs the branch locally: the frontend on $WEB and the backend on $API. The staging probe script is pointed at this local stack through its own environment variables. Nothing here touches staging.

**A provider with no API key.** The frontend is started with `EMAIL_SERVICE_PROVIDER=resend` and no key. The route says so without authentication, and the probe fails and names the reason.

```bash
curl -s -i "$WEB/api/health" | grep -i -E "^HTTP|^cache-control|^\{" | tr -d "\r"
python3 "$WT/scripts/staging_health_probe.py"; echo "probe exit code: $?"
```

```output
HTTP/1.1 200 OK
cache-control: no-store
{"status":"ok","email":{"configured":false,"provider":null}}
attempt 1/1 failed: http://localhost:3102/api/health -> 200 '{"status":"ok","email":{"configured":false,"provider":null}}': no email provider is configured, so no new account can verify its address
probe exit code: 1
```

**A provider with a key.** The frontend is restarted with a key set (a placeholder; nothing is sent). The route reports the provider by name, the key is not in the response, and the probe passes.

```bash
curl -s "$WEB/api/health"; echo
echo "responses containing the key: $(curl -s -i "$WEB/api/health" | grep -c "demo-not-a-real-key")"
python3 "$WT/scripts/staging_health_probe.py"; echo "probe exit code: $?"
```

```output
{"status":"ok","email":{"configured":true,"provider":"resend"}}
responses containing the key: 0
healthy: http://localhost:8100/api/v1/health, http://localhost:3102/ and its email provider (attempt 1/1)
probe exit code: 0
```

**Tests.** The named tests: the rule the route reports, held to what a send does; the route; and the probe against a local stand-in server.

```bash
cd "$WT/frontend" && npx jest src/lib/__tests__/email.test.ts src/app/api/health -t "emailProvider|GET /api/health" --verbose --reporters=default 2>&1 | grep -E "✓|✕" | sed "s/ ([0-9]* ms)//" | sort
cd "$WT/scripts" && uvx --with pytest --with pyyaml pytest test_staging_triggers.py -q -k "probe" 2>&1 | tail -1 | sed "s/ in [0-9.]*s//"
```

```output
      ✓ development, nothing set
      ✓ production, Resend with a key
      ✓ production, Resend without a key
      ✓ production, SendGrid with a key
      ✓ production, console
      ✓ production, nothing set
      ✓ production, unknown provider
    ✓ never returns the key and is not cached
    ✓ reports a configured provider by name
    ✓ reports email as not configured when no provider is set
    ✓ reports email as not configured when the provider has no API key
    ✓ reports email as not configured when the provider is unknown
11 passed, 2 deselected
```

Not shown: staging. This build is not deployed there yet; the route is what makes it possible to check staging from outside before relying on sign-up. "Configured" means a known provider and a key are present, not that the key is valid.
