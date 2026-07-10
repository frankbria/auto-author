# Issue #189 — [P1.9] Backend binds 0.0.0.0 on shared VPS

**Plan source**: self-authored (no plan comment on the issue).
**Approved**: autonomously (no architectural fork — the AC's first branch, bind loopback, is clearly right; the verified ufw firewall is documented as defense-in-depth, covering the OR branch too).

## Findings (verified live on staging 2026-07-10)
- Backend listens `0.0.0.0:8000`, Next listens `*:3002` (confirmed via `ss -tlnp`).
- ufw is ACTIVE, default-deny: only 22/80/443 allowed. External curl to `195.35.14.177:8000/3002` times out — the firewall already blocks direct access, but nothing in the repo documents/verifies it.
- nginx vhosts proxy to `http://localhost:8000` / `http://localhost:3002`; `/etc/hosts` maps `localhost` to both `127.0.0.1` and `::1`.

## Plan (AC branch 1: bind loopback; + document firewall as branch 2 evidence)
- [ ] `ecosystem.config.template.js`: backend `--host 127.0.0.1`; frontend `args: 'start -- -H 127.0.0.1'`
- [ ] `scripts/deploy.sh:110`, `scripts/deploy-fixed.sh:191`: `--host 127.0.0.1`
- [ ] `.github/workflows/deploy-production.yml.disabled:201`: same (drift prevention if re-enabled)
- [ ] `docs/STAGING-DEPLOYMENT.md`: document loopback binding + the verified ufw baseline
- [ ] Server-side (ops, during demo): nginx `proxy_pass` → explicit `127.0.0.1` (avoids ::1 failover retries), apply loopback bind to running PM2 config, verify site still serves + ports loopback-only
- [ ] No unit tests: config-only change; verification is the live demo (ss output + https round trip)
