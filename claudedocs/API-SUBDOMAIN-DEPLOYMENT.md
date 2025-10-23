# API Subdomain Separation Deployment
**Date**: 2025-10-19
**Status**: ✅ Complete
**Environment**: ClawCloud Production (47.88.89.175)

---

## Executive Summary

Successfully separated Auto-Author frontend and API into distinct subdomains to resolve architectural issues where API documentation routes conflicted with Next.js frontend routes.

**Before**:
- Frontend + API: https://dev.autoauthor.app (mixed routing)
- Swagger docs at /docs conflicted with Next.js pages

**After**:
- Frontend: https://dev.autoauthor.app (clean Next.js routing)
- API: https://api.dev.autoauthor.app (dedicated API subdomain)
- Swagger docs: https://api.dev.autoauthor.app/docs (no conflicts)

---

## Changes Implemented

### 1. Backend CSP Headers (middleware.py)
**File**: `backend/app/api/middleware.py`

**Changes**:
```python
# Before (lines 52-60):
"script-src 'self' https://clerk.your-domain.com; "
"style-src 'self' 'unsafe-inline'; "
"font-src 'self';"

# After:
"script-src 'self' 'unsafe-inline' https://clerk.your-domain.com https://cdn.jsdelivr.net; "
"style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
"img-src 'self' data: https://img.clerk.com https://fastapi.tiangolo.com; "
"font-src 'self' data: https://r2cdn.perplexity.ai;"
```

**Reason**: Allow Swagger UI to load external resources (scripts, styles, fonts, images)

---

### 2. Frontend CSP Headers (next.config.ts)
**File**: `frontend/next.config.ts`

**Changes**:
```typescript
// Line 27 - Added api.dev.autoauthor.app to connect-src:
"connect-src 'self' https://clerk.auto-author.dev https://*.clerk.accounts.dev https://api.auto-author.dev https://api.dev.autoauthor.app https://clerk-telemetry.com https://dev.autoauthor.app http://localhost:8000 https://localhost:8000 wss:"
```

**Reason**: Allow frontend to make API requests to new subdomain

---

### 3. Backend CORS Configuration
**File**: `/opt/auto-author/current/backend/.env` (server)

**Changes**:
```bash
# Before:
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]

# After:
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8000","https://dev.autoauthor.app"]
```

**Reason**: Allow cross-origin requests from frontend subdomain

---

### 4. Frontend Environment Configuration
**File**: `/opt/auto-author/current/frontend/.env.production` (server)

**Changes**:
```bash
# Before: (not deployed correctly)
NEXT_PUBLIC_API_URL=https://dev.autoauthor.app/api/v1

# After:
NEXT_PUBLIC_API_URL=https://api.dev.autoauthor.app/api/v1
```

**Reason**: Point frontend to new API subdomain

---

### 5. Clerk JWT Public Key Fix
**File**: `/opt/auto-author/current/backend/.env` (server)

**Issue**: JWT verification was failing with `InvalidData(InvalidByte(384, 92))` error

**Root Cause**: The CLERK_JWT_PUBLIC_KEY had incorrect format - literal backslash-n strings instead of escaped newlines for .env format

**Solution**:
1. Fetched correct public key from Clerk's JWKS endpoint
2. Converted JWK to PEM format
3. Escaped newlines properly: `\n` → `\\n` for .env file
4. Key is converted back to actual newlines by config.py `clerk_jwt_public_key_pem` property

**Correct Format**:
```bash
CLERK_JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAveex50e6CDsKHJGphFUX\\nf6ljJcmMzwS5sSDa9iYix+m6rGHLlX/8s78DJmkXADLeg8HBdRTBnhkJw/0l/ik4\\nJ2pc31Q1p2Jsg58EZ2tQiqXmgH7dRNn2wi+TWwD06EMABJjs+FCf2/01OVBux+TT\\n1AJmiLC1mYd4jDcuZiSoU0+HoxvNE1KxIuNaU8kN7Dn7qeWvtP/iZIdCopYlFFVm\\nqYy1kAd1+uPjtJm7agjH+9rhDPifEGuxd/SGHRT9E3bhUPfzUX4t4avfe0D34qtS\\ndulHnweLJXwM/j2ZH7FBj0MUYfQPrbanoKRq5CaRxlxc3n45BQSAR1nbkEx+qWeX\\n6wIDAQAB\\n-----END PUBLIC KEY-----\\n"
```

**Conversion Code**:
```python
# Fetch JWKS and convert to PEM
curl -s https://delicate-ladybird-47.clerk.accounts.dev/.well-known/jwks.json | python3 -c "
import json, sys, base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

jwks = json.load(sys.stdin)
key = jwks['keys'][0]
n = int.from_bytes(base64.urlsafe_b64decode(key['n'] + '=='), 'big')
e = int.from_bytes(base64.urlsafe_b64decode(key['e'] + '=='), 'big')
public_numbers = rsa.RSAPublicNumbers(e, n)
public_key = public_numbers.public_key(default_backend())
pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8')
print(pem.replace('\n', '\\\\n'))
"
```

---

### 6. Nginx Configuration (Server-Side)
**Files**: `/etc/nginx/sites-available/dev.autoauthor.app`, `/etc/nginx/sites-available/api.dev.autoauthor.app`

**dev.autoauthor.app** (Frontend Only):
```nginx
server {
    listen 80;
    listen [::]:80;
    server_name dev.autoauthor.app;

    location / {
        proxy_pass http://localhost:3002;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**api.dev.autoauthor.app** (Backend Only):
```nginx
server {
    listen 80;
    listen [::]:80;
    server_name api.dev.autoauthor.app;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**SSL**: User configured Let's Encrypt SSL certificates for both subdomains

---

## Deployment Steps Performed

### 1. Local Development
1. Updated `backend/app/api/middleware.py` CSP headers
2. Updated `frontend/next.config.ts` CSP and API URL
3. Updated `frontend/.env.production.local` with new API URL
4. Committed changes to `fix/api-subdomain-csp` branch
5. Pushed branch to GitHub

### 2. Server Deployment
1. Created deployment tarball (excluding node_modules, .next, __pycache__)
2. Copied tarball to server: `scp auto-author-clawcloud.tar.gz root@47.88.89.175:/opt/auto-author/`
3. Extracted on server: `tar -xzf auto-author-clawcloud.tar.gz -C current/`
4. Updated backend `.env`:
   - Added `https://dev.autoauthor.app` to BACKEND_CORS_ORIGINS
   - Fixed CLERK_JWT_PUBLIC_KEY format
5. Updated frontend `.env.production` with `NEXT_PUBLIC_API_URL=https://api.dev.autoauthor.app/api/v1`
6. Installed frontend dependencies: `npm install`
7. Rebuilt frontend: `npm run build`
8. Restarted both PM2 processes:
   - `pm2 restart auto-author-backend`
   - `pm2 restart auto-author-frontend`

### 3. DNS Configuration
User configured DNS A records:
- `dev.autoauthor.app` → 47.88.89.175
- `api.dev.autoauthor.app` → 47.88.89.175

### 4. SSL Configuration
User configured Let's Encrypt certificates for both subdomains

---

## Testing & Verification

### CORS Verification
```bash
curl -I -X OPTIONS https://api.dev.autoauthor.app/api/v1/books/ \
  -H "Origin: https://dev.autoauthor.app" \
  -H "Access-Control-Request-Method: GET" | grep access-control

# Result:
# access-control-allow-origin: https://dev.autoauthor.app ✅
# access-control-allow-credentials: true ✅
# access-control-allow-methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT ✅
```

### CSP Verification
```bash
curl -I https://api.dev.autoauthor.app/docs | grep content-security-policy

# Result: Includes cdn.jsdelivr.net, fastapi.tiangolo.com, r2cdn.perplexity.ai ✅
```

### API Health Check
```bash
curl -v https://api.dev.autoauthor.app/api/v1/books/ -H "Origin: https://dev.autoauthor.app" 2>&1 | grep "< HTTP"

# Result: HTTP/2 403 (correct - requires authentication) ✅
# Result includes: access-control-allow-origin: https://dev.autoauthor.app ✅
```

### Frontend Connection Test
- Browser navigation to https://dev.autoauthor.app ✅
- Sign in via Clerk ✅
- Dashboard loads ✅
- API requests to api.dev.autoauthor.app succeed ✅
- No CORS errors in console ✅
- No CSP violations in console ✅

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   Users (Internet)                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Nginx (Port 80/443 SSL)                        │
│  - dev.autoauthor.app → localhost:3002                      │
│  - api.dev.autoauthor.app → localhost:8000                  │
└────────┬──────────────────────────┬─────────────────────────┘
         │                          │
         ▼                          ▼
┌──────────────────┐      ┌──────────────────────┐
│  PM2: Frontend   │      │  PM2: Backend        │
│  Port: 3002      │      │  Port: 8000          │
│  Next.js         │◄────►│  FastAPI + Uvicorn   │
│                  │ API  │                      │
│  CSP: allows     │      │  CSP: allows         │
│  - api.dev...    │      │  - cdn.jsdelivr.net  │
│  - clerk domains │      │  - fastapi.tiangolo  │
└──────────────────┘      └──────────────────────┘
         │                          │
         │                          ▼
         │                ┌──────────────────────┐
         │                │  MongoDB (Motor)     │
         │                │  Database: auto_...  │
         │                └──────────────────────┘
         │
         ▼
┌──────────────────────┐
│  Clerk Auth (SaaS)   │
│  JWT Verification    │
└──────────────────────┘
```

---

## Lessons Learned

### 1. Monorepo CORS Verification Critical
**Issue**: Deployed without verifying CORS headers on server
**Impact**: Frontend couldn't connect to API, blocking all functionality
**Solution**: Always verify CORS with curl after monorepo deployment

**Best Practice**:
```bash
# Add to deployment checklist:
curl -I -X OPTIONS https://api.domain.com/api/v1/endpoint \
  -H "Origin: https://frontend.domain.com" \
  -H "Access-Control-Request-Method: GET"
```

### 2. JWT Key Format in .env Files
**Issue**: Literal `\n` in .env vs escaped `\\n` caused JWT verification failure
**Impact**: 500 errors on all authenticated endpoints
**Solution**: Use double-escaped newlines in .env, convert with property

**Correct Pattern**:
```python
# In config.py:
@property
def clerk_jwt_public_key_pem(self):
    return self.CLERK_JWT_PUBLIC_KEY.replace("\\n", "\n")
```

### 3. NEXT_PUBLIC_* Variables Require Rebuild
**Issue**: Changed API URL but frontend still used old URL
**Impact**: Frontend continued calling wrong endpoint
**Solution**: Remember NEXT_PUBLIC_* vars are baked in at build time

**Best Practice**: Always rebuild frontend after changing environment variables

### 4. CSP Headers Need Both Domains
**Issue**: Added backend resources but forgot frontend needs API subdomain
**Impact**: CSP blocked API connections from frontend
**Solution**: Update CSP on both frontend and backend for cross-domain communication

### 5. Systematic Investigation Prevents Mistakes
**Issue**: Initially confused Docker containers with host processes
**Impact**: Could have damaged unrelated applications (sprintforge)
**Solution**: Created comprehensive server audit before making changes

---

## Rollback Plan

If deployment fails:

1. **Revert Frontend .env**:
   ```bash
   ssh root@47.88.89.175 "echo 'NEXT_PUBLIC_API_URL=https://dev.autoauthor.app/api/v1' > /opt/auto-author/current/frontend/.env.production"
   ```

2. **Revert CORS**:
   ```bash
   ssh root@47.88.89.175 'sed -i "s|BACKEND_CORS_ORIGINS=.*|BACKEND_CORS_ORIGINS=[\"http://localhost:3000\",\"http://localhost:8000\"]|" /opt/auto-author/current/backend/.env'
   ```

3. **Revert Nginx**:
   - Remove api.dev.autoauthor.app config
   - Restore mixed routing to dev.autoauthor.app

4. **Rebuild & Restart**:
   ```bash
   ssh root@47.88.89.175 "cd /opt/auto-author/current/frontend && npm run build && pm2 restart all"
   ```

---

## Future Improvements

1. **Docker Containerization**: Move both frontend and backend to Docker for consistency
2. **CI/CD Pipeline**: Automate deployment with GitHub Actions
3. **Environment Validation**: Pre-deployment script to verify CORS, CSP, and env vars
4. **Health Checks**: Add /health endpoints and monitoring
5. **Staging Environment**: Separate staging server before production deployment
6. **Automated Testing**: E2E tests that run against deployed environment

---

## References

- Server Deployment Audit: `claudedocs/SERVER-DEPLOYMENT-AUDIT-2025-10-19.md`
- Testing Guide: `claudedocs/DEPLOYMENT-TESTING-GUIDE.md`
- SSH Hardening Script: `scripts/harden-ssh.sh`
- Frontend CSP Config: `frontend/next.config.ts:27`
- Backend CSP Config: `backend/app/api/middleware.py:52-60`
- Backend Config: `backend/app/core/config.py:22-23, 38-40`
