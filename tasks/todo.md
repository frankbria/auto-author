# Issue #189 — [P1.9] Backend binds 0.0.0.0 on shared VPS

**Plan source**: self-authored (no plan comment on the issue).
**Approved**: autonomously (no architectural fork — the AC's first branch, bind loopback, is clearly right; the verified ufw firewall is documented as defense-in-depth, covering the OR branch too).

## Findings (verified live on staging 2026-07-10)
- Backend listens `0.0.0.0:8000`, Next listens `*:3002` (confirmed via `ss -tlnp`).
- ufw is ACTIVE, default-deny: only 22/80/443 allowed. External curl to `195.35.14.177:8000/3002` times out — the firewall already blocks direct access, but nothing in the repo documents/verifies it.
- nginx vhosts proxy to `http://localhost:8000` / `http://localhost:3002`; `/etc/hosts` maps `localhost` to both `127.0.0.1` and `::1`.

## Plan (AC branch 1: bind loopback; + document firewall as branch 2 evidence)
- [x] `ecosystem.config.template.js`: backend `--host 127.0.0.1`; frontend `args: 'start -- -H 127.0.0.1'`
- [x] `scripts/deploy.sh`, `scripts/deploy-fixed.sh`: backend AND frontend start lines loopback (frontend lines were opencode round-1 Major)
- [x] `.github/workflows/deploy-production.yml.disabled`: same (drift prevention if re-enabled)
- [x] `docs/STAGING-DEPLOYMENT.md`: Network Exposure section + manual examples fixed
- [x] Server-side (ops, applied live in demo): nginx `proxy_pass` → explicit `127.0.0.1`, deployed ecosystem.config.js patched, pm2 restarted — ss loopback-only, https 200, external ports dead
- [x] Post-PR minor: legacy scripts' health checks curl 127.0.0.1 explicitly
- [x] No unit tests: config-only change; demo is the verification (docs/demos/2026-07-10-issue-189-loopback-bind.md)

## Status: PR #268 open, reviews clean (opencode pre-PR ×2 + post-PR fresh), demo done, awaiting CI → merge
