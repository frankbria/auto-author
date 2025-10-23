# Server Deployment Architecture Audit
**Date**: 2025-10-19
**Server**: ClawCloud Production (47.88.89.175)
**Status**: CRITICAL - Auto-Author Backend Not Running

---

## Executive Summary

**CRITICAL ISSUE**: Auto-Author backend is **NOT RUNNING**. All 401 authentication errors are because nginx is proxying to `localhost:8000` where nothing is listening.

**ROOT CAUSE OF CONFUSION**:
- Docker container `sprintforge-staging-backend` has internal port 8000
- This led to false assumption auto-author backend was running in Docker
- Actually: sprintforge is completely separate, auto-author backend never started

**SAFETY**: No cross-application pollution occurred. All applications properly isolated.

---

## Applications Running on Server

### 1. Auto-Author (dev.autoauthor.app)
**Status**: Frontend ✅ | Backend ❌

- **Frontend**: PM2 process `auto-author-frontend` (PID 153303)
  - Port: 3002
  - Status: Running normally
  - Process Manager: PM2

- **Backend**: **NOT RUNNING**
  - Expected Port: 8000
  - Actual Port: Nothing listening
  - Process Manager: Should be PM2 but not started
  - Environment File: `/opt/auto-author/current/backend/.env` (exists but unused)

**Nginx Config**:
```nginx
server_name dev.autoauthor.app;
location / { proxy_pass http://localhost:3002; }      # Frontend - WORKING
location /api/ { proxy_pass http://localhost:8000; }  # Backend - FAILING (nothing there)
```

---

### 2. FrankBria.com / Bear Adventures (beta.frankbria.com)
**Status**: ✅ All Running

- **Strapi CMS**: PM2 process `strapi` (PID 1902)
  - Port: 1337
  - Status: Running (5h uptime)

- **Next.js Frontend**: PM2 process `frankbria-nextjs` (PID 1914)
  - Port: 3001
  - Status: Running (5h uptime)

**Nginx Config**:
```nginx
server_name beta.frankbria.com;
location / { proxy_pass http://localhost:3001; }
location /admin { proxy_pass http://localhost:1337; }
location /api { proxy_pass http://localhost:1337; }
```

---

### 3. Sprintforge (localhost:8080)
**Status**: ✅ Complete Docker Stack Running

**Docker Containers**:
- `sprintforge-staging-backend` (94e9b611cae5)
  - Image: sprintforge-backend
  - Port: 8000/tcp (INTERNAL ONLY, not exposed to host)
  - Status: Healthy, Up 9 minutes

- `sprintforge-staging-frontend` (41d97725cb39)
  - Port: 3000/tcp (internal)
  - Status: Unhealthy (unrelated to auto-author)

- `sprintforge-staging-nginx` (bc12c61d6c75)
  - Port: 0.0.0.0:8080->80/tcp (EXPOSED)
  - Routes internal Docker network traffic

- `sprintforge-staging-db` (postgres:15-alpine)
- `sprintforge-staging-redis` (redis:7-alpine)
- `sprintforge-watchtower` (auto-updates)

**Network Isolation**: Complete Docker network isolation. Does NOT interact with host ports 8000, 3002, etc.

---

## Port Allocation

| Port | Application | Process Type | Status |
|------|-------------|--------------|--------|
| 80   | nginx (all domains) | System Service | ✅ Running |
| 443  | nginx SSL | System Service | ✅ Running |
| 1337 | Strapi CMS | PM2 | ✅ Running |
| 3000 | Sprintforge frontend | Docker (internal) | ✅ Running |
| 3001 | FrankBria Next.js | PM2 | ✅ Running |
| 3002 | Auto-Author frontend | PM2 | ✅ Running |
| **8000** | **Auto-Author backend** | **NONE** | **❌ NOT RUNNING** |
| 8080 | Sprintforge nginx | Docker (exposed) | ✅ Running |

---

## Process Management

### PM2 Managed (Host System)
```
ID  Name                   PID      Status    Memory
6   auto-author-frontend   153303   online    59.8mb
1   frankbria-nextjs       1914     online    67.5mb
0   strapi                 1902     online    66.9mb
```

### Docker Managed (Isolated Network)
All sprintforge-* containers running in Docker

---

## Environment Variables Safety

### Isolation Check:
✅ **NO CROSS-POLLUTION**

- Auto-Author backend .env: `/opt/auto-author/current/backend/.env` (host filesystem)
  - Modified during debugging session
  - Contains correct CLERK_JWT_PUBLIC_KEY (single-line format)
  - **NOT BEING USED** (no backend process reading it)

- Sprintforge backend env: Docker container environment (isolated)
  - Completely separate from host .env files
  - Cannot be accidentally modified from host

- Other applications: Use their own .env files in separate directories

**Conclusion**: The .env edits I made only affected the auto-author backend file. No other applications were impacted.

---

## Why Backend Not Running

**Historical Context** (from conversation):
- User deployed auto-author to server previously
- Frontend started successfully with PM2
- Backend was supposed to start with PM2 but **appears to have failed or never started**
- User reported 401 errors, indicating auth failure
- Actual issue: No backend process to authenticate against

**Expected Start Command** (from deployment script):
```bash
cd /opt/auto-author/current/backend
pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 8000" --name "auto-author-backend"
```

---

## Corrective Actions Needed

### Immediate (Fix Auth 401 Errors)
1. ✅ Verified .env file has correct CLERK_JWT_PUBLIC_KEY
2. ❌ **Start the backend process with PM2**
3. ❌ Verify backend health endpoint responds
4. ❌ Test authentication flow

### Medium Term (Deployment Isolation)
1. Create separate deployment scripts per application
2. Document port allocations to prevent conflicts
3. Add health check monitoring
4. Implement proper process supervision (systemd or PM2 startup)

### Long Term (Production Best Practices)
1. Consider Docker for all applications (consistency)
2. Implement container orchestration (docker-compose)
3. Separate staging vs production servers
4. Add CI/CD deployment automation

---

## Lessons Learned

1. **Docker container names can be misleading**: `sprintforge-staging-backend` on port 8000 led to false assumption
2. **Always verify process actually listening on port**: `ss -tlnp` or `lsof -i :PORT` before debugging
3. **PM2 list doesn't show failed starts**: Backend may have crashed on startup - need to check logs
4. **Systematic investigation prevents mistakes**: Could have damaged sprintforge if hadn't stopped to audit

---

## Next Steps

**Recommended Approach**:
1. Review why backend didn't start originally (check PM2 logs if available)
2. Ensure Python environment properly set up
3. Start backend with PM2 monitoring
4. Verify authentication works
5. Save PM2 config for auto-restart on reboot

**Questions for User**:
- Was the backend ever successfully running on this server?
- Should we investigate why it didn't start from original deployment?
- Do you want systemd service for auto-start on reboot?
