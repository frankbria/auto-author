# Auto-Author Deployment Testing Guide
**Date**: 2025-10-19
**Environment**: ClawCloud Production Server (dev.autoauthor.app)
**Sprint**: API Subdomain Separation & Authentication Fix

---

## Pre-Testing Checklist

Before beginning UI tests, verify the deployment is healthy:

```bash
# Check both PM2 processes are running
ssh root@47.88.89.175 "pm2 status"
# Expected: auto-author-frontend (online), auto-author-backend (online)

# Verify CORS configuration
curl -I -X OPTIONS https://api.dev.autoauthor.app/api/v1/books \
  -H "Origin: https://dev.autoauthor.app" \
  -H "Access-Control-Request-Method: GET" | grep access-control

# Expected: access-control-allow-origin: https://dev.autoauthor.app

# Test API health
curl -s https://api.dev.autoauthor.app/ | head -20
# Expected: {"message":"Welcome to the Auto Author API"...}
```

---

## UI Testing Steps

### 1. Homepage & Initial Load
**URL**: https://dev.autoauthor.app

**Test**:
1. Navigate to https://dev.autoauthor.app
2. Verify homepage loads without errors
3. Open browser DevTools (F12) → Console tab
4. Confirm NO CORS errors
5. Confirm NO CSP violations

**Expected Results**:
- ✅ Page loads successfully
- ✅ No red errors in console
- ✅ Clerk sign-in button visible
- ✅ No "blocked by CORS policy" messages
- ✅ No "refused to load" CSP errors

**Common Issues**:
- CSP errors for connect-src → Check frontend next.config.ts includes api.dev.autoauthor.app
- CORS errors → Check backend .env BACKEND_CORS_ORIGINS includes dev.autoauthor.app

---

### 2. User Authentication
**URL**: https://dev.autoauthor.app

**Test**:
1. Click "Sign In" button
2. Complete Clerk authentication flow
3. Verify redirect back to app after sign-in
4. Check Network tab for auth token requests

**Expected Results**:
- ✅ Clerk modal opens without CSP errors
- ✅ Sign-in completes successfully
- ✅ Redirected to /dashboard after authentication
- ✅ JWT token stored in browser (check Application → Local Storage)

**Common Issues**:
- Clerk CSP errors → Check next.config.ts script-src and frame-src allow *.clerk.accounts.dev
- Redirect fails → Check NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY in .env.production

---

### 3. Dashboard & Books List
**URL**: https://dev.autoauthor.app/dashboard

**Test**:
1. Navigate to /dashboard after sign-in
2. Wait for books list to load
3. Open DevTools Network tab
4. Look for GET request to https://api.dev.autoauthor.app/api/v1/books/
5. Check response status and CORS headers

**Expected Results**:
- ✅ Dashboard loads without errors
- ✅ API request to api.dev.autoauthor.app succeeds (200 OK or 403 if no books)
- ✅ Response includes access-control-allow-origin header
- ✅ No CORS preflight failures
- ✅ Books display (if user has books) or empty state shows

**Common Issues**:
- 401 Unauthorized → Check CLERK_JWT_PUBLIC_KEY in backend .env (must be escaped \n)
- 500 Internal Server Error → Check backend logs: `ssh root@47.88.89.175 "pm2 logs auto-author-backend --lines 50"`
- CORS blocked → Verify BACKEND_CORS_ORIGINS in backend .env includes "https://dev.autoauthor.app"

---

### 4. Create New Book
**URL**: https://dev.autoauthor.app/dashboard/new-book

**Test**:
1. Click "New Book" or navigate to /dashboard/new-book
2. Fill in book title and description
3. Submit the form
4. Monitor Network tab for POST to /api/v1/books/

**Expected Results**:
- ✅ Form loads correctly
- ✅ POST request to api.dev.autoauthor.app/api/v1/books/ succeeds
- ✅ Authorization header includes Bearer token
- ✅ Redirect to book detail page after creation
- ✅ New book appears in books list

**Common Issues**:
- 403 Forbidden → JWT token invalid, check clerk_jwt_public_key_pem property conversion
- Request fails silently → Check CSP connect-src allows api.dev.autoauthor.app

---

### 5. API Documentation Access
**URL**: https://api.dev.autoauthor.app/docs

**Test**:
1. Navigate to https://api.dev.autoauthor.app/docs
2. Verify Swagger UI loads completely
3. Check browser console for resource loading errors
4. Try expanding an endpoint

**Expected Results**:
- ✅ Swagger UI interface displays
- ✅ No CSP errors blocking cdn.jsdelivr.net or fastapi.tiangolo.com
- ✅ All CSS/JS resources load successfully
- ✅ Endpoints are expandable and interactive

**Common Issues**:
- White page → Check backend middleware.py CSP headers allow cdn.jsdelivr.net
- Missing favicon → Check CSP allows fastapi.tiangolo.com
- Style issues → Check CSP style-src allows cdn.jsdelivr.net

---

## Regression Testing

After deployment changes, test these critical paths:

### Authentication Flow
1. Sign out → Sign in → Dashboard → Books list loads

### Book Management
1. Create book → View book → Edit TOC → Generate chapters

### Chapter Editing
1. Open chapter → Rich text editor loads → Auto-save works → Voice input (if enabled)

### Export Functionality
1. Open book → Export → PDF/DOCX download works

---

## Performance Validation

Check Core Web Vitals:

1. Open DevTools → Lighthouse tab
2. Run Performance audit
3. Verify scores:
   - **LCP** (Largest Contentful Paint): < 2.5s
   - **FID** (First Input Delay): < 100ms
   - **CLS** (Cumulative Layout Shift): < 0.1

---

## Security Validation

### CSP Headers Check
```bash
# Frontend CSP
curl -I https://dev.autoauthor.app | grep content-security-policy

# Backend CSP
curl -I https://api.dev.autoauthor.app/docs | grep content-security-policy
```

**Expected**:
- Frontend allows: dev.autoauthor.app, clerk domains, api.dev.autoauthor.app
- Backend allows: cdn.jsdelivr.net, fastapi.tiangolo.com, r2cdn.perplexity.ai

### CORS Verification
```bash
# Test CORS preflight
curl -I -X OPTIONS https://api.dev.autoauthor.app/api/v1/books/ \
  -H "Origin: https://dev.autoauthor.app" \
  -H "Access-Control-Request-Method: GET"
```

**Expected Headers**:
- `access-control-allow-origin: https://dev.autoauthor.app`
- `access-control-allow-credentials: true`
- `access-control-allow-methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT`

---

## Troubleshooting Guide

### Issue: "Access blocked by CORS policy"
**Diagnosis**:
```bash
ssh root@47.88.89.175 "grep BACKEND_CORS_ORIGINS /opt/auto-author/current/backend/.env"
```

**Fix**:
```bash
# Add dev.autoauthor.app to CORS origins
ssh root@47.88.89.175 'sed -i "s|BACKEND_CORS_ORIGINS=.*|BACKEND_CORS_ORIGINS=[\"http://localhost:3000\",\"http://localhost:8000\",\"https://dev.autoauthor.app\"]|" /opt/auto-author/current/backend/.env'
ssh root@47.88.89.175 "pm2 restart auto-author-backend"
```

### Issue: "Failed to fetch" / 500 errors
**Diagnosis**:
```bash
ssh root@47.88.89.175 "pm2 logs auto-author-backend --lines 50 --nostream | grep -A 10 'Error\|500\|Traceback'"
```

**Common Causes**:
- JWT key format incorrect (InvalidByte error at position 384)
- MongoDB not running
- Backend environment variables missing

**JWT Key Fix**:
```bash
# Get correct key from Clerk JWKS
curl -s https://delicate-ladybird-47.clerk.accounts.dev/.well-known/jwks.json | \
  python3 -c "import json, sys, base64; from cryptography.hazmat.primitives import serialization; from cryptography.hazmat.primitives.asymmetric import rsa; from cryptography.hazmat.backends import default_backend; jwks = json.load(sys.stdin); key = jwks['keys'][0]; n = int.from_bytes(base64.urlsafe_b64decode(key['n'] + '=='), 'big'); e = int.from_bytes(base64.urlsafe_b64decode(key['e'] + '=='), 'big'); public_numbers = rsa.RSAPublicNumbers(e, n); public_key = public_numbers.public_key(default_backend()); pem = public_key.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode('utf-8'); print(pem.replace('\n', '\\\\n'))"

# Update on server
ssh root@47.88.89.175 'KEY="[paste_key_here]" && sed -i "s|CLERK_JWT_PUBLIC_KEY=.*|CLERK_JWT_PUBLIC_KEY=\"$KEY\"|" /opt/auto-author/current/backend/.env && pm2 restart auto-author-backend'
```

### Issue: Swagger UI blank/white page
**Diagnosis**:
- Check browser console for CSP violations
- Look for "refused to load" messages

**Fix**:
- Update backend/app/api/middleware.py CSP headers to whitelist:
  - script-src: https://cdn.jsdelivr.net
  - style-src: https://cdn.jsdelivr.net
  - img-src: https://fastapi.tiangolo.com
  - font-src: https://r2cdn.perplexity.ai, data:

### Issue: Frontend can't connect to API
**Diagnosis**:
```bash
# Check frontend environment
ssh root@47.88.89.175 "cat /opt/auto-author/current/frontend/.env.production | grep NEXT_PUBLIC_API_URL"
```

**Expected**: `NEXT_PUBLIC_API_URL=https://api.dev.autoauthor.app/api/v1`

**Fix** (requires rebuild):
```bash
ssh root@47.88.89.175 "cat > /opt/auto-author/current/frontend/.env.production << 'EOF'
NEXT_PUBLIC_API_URL=https://api.dev.autoauthor.app/api/v1
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_ZGVsaWNhdGUtbGFkeWJpcmQtNDcuY2xlcmsuYWNjb3VudHMuZGV2JA
CLERK_SECRET_KEY=sk_test_yxycVoEwI4EzhsYAJ8g0Re8VBKClBrfoQC5OTnS6zE
NEXT_PUBLIC_ENVIRONMENT=production
PORT=3002
EOF
"
ssh root@47.88.89.175 "cd /opt/auto-author/current/frontend && npm run build && pm2 restart auto-author-frontend"
```

---

## Success Criteria

Deployment is considered successful when:

1. ✅ All Pre-Testing Checklist items pass
2. ✅ User can sign in via Clerk authentication
3. ✅ Dashboard loads and displays books without CORS errors
4. ✅ User can create a new book
5. ✅ User can edit book content (chapters, TOC)
6. ✅ API documentation at api.dev.autoauthor.app/docs loads completely
7. ✅ No CSP violations in browser console
8. ✅ No 500 errors in backend logs
9. ✅ All API requests return correct CORS headers
10. ✅ Core Web Vitals meet performance thresholds

---

## Rollback Procedure

If critical issues arise:

1. **Identify the issue**:
   ```bash
   ssh root@47.88.89.175 "pm2 logs --lines 100"
   ```

2. **Restore previous deployment** (if tarball backup exists):
   ```bash
   ssh root@47.88.89.175 "cd /opt/auto-author && tar -xzf backup-[timestamp].tar.gz -C current/ && pm2 restart all"
   ```

3. **Revert nginx config** (if subdomain separation causes issues):
   ```bash
   ssh root@47.88.89.175 "cd /etc/nginx/sites-available && cp dev.autoauthor.app.backup dev.autoauthor.app && nginx -t && systemctl reload nginx"
   ```

4. **Restore environment variables**:
   ```bash
   ssh root@47.88.89.175 "cp /opt/auto-author/current/backend/.env.backup /opt/auto-author/current/backend/.env && pm2 restart auto-author-backend"
   ```

---

## Contact & Support

**Server**: ClawCloud Production - 47.88.89.175
**SSH Access**: root@47.88.89.175 (key-based auth)
**Process Manager**: PM2
**Process Names**: auto-author-frontend, auto-author-backend

**Logs**:
- Frontend: `pm2 logs auto-author-frontend`
- Backend: `pm2 logs auto-author-backend`
- Nginx: `/var/log/nginx/error.log`, `/var/log/nginx/access.log`
