# Auto-Author Deployment Testing Checklist
**Environment**: ClawCloud Production (dev.autoauthor.app)
**Date**: _____________
**Tester**: _____________

---

## Pre-Flight Checks

### Server Health
- [ ] SSH into server: `ssh root@47.88.89.175`
- [ ] Check PM2 processes: `pm2 status`
  - [ ] `auto-author-frontend` shows **online**
  - [ ] `auto-author-backend` shows **online**
- [ ] Check backend logs for errors: `pm2 logs auto-author-backend --lines 20 --nostream`
  - [ ] No **Traceback** or **Error** messages in last 20 lines
- [ ] Check frontend logs: `pm2 logs auto-author-frontend --lines 20 --nostream`
  - [ ] Shows "✓ Ready" message

### CORS Configuration
- [ ] Test CORS preflight:
```bash
curl -I -X OPTIONS https://api.dev.autoauthor.app/api/v1/books/ \
  -H "Origin: https://dev.autoauthor.app" \
  -H "Access-Control-Request-Method: GET" | grep access-control
```
- [ ] Response includes: `access-control-allow-origin: https://dev.autoauthor.app`
- [ ] Response includes: `access-control-allow-credentials: true`

### API Health
- [ ] Test API endpoint:
```bash
curl -s https://api.dev.autoauthor.app/ | head -20
```
- [ ] Response includes: `"message":"Welcome to the Auto Author API"`
- [ ] No error messages

---

## UI Testing - Frontend

### 1. Homepage Load
- [ ] Open browser (Chrome/Firefox/Safari)
- [ ] Navigate to: `https://dev.autoauthor.app`
- [ ] Page loads without errors
- [ ] Open DevTools (F12) → **Console** tab
- [ ] **No red error messages** in console
- [ ] **No CORS errors** (check for "blocked by CORS policy")
- [ ] **No CSP errors** (check for "refused to load")
- [ ] Clerk sign-in button is visible

**If errors found, note here**:
_______________________________________________

---

### 2. User Sign-In
- [ ] Click "Sign In" button
- [ ] Clerk authentication modal opens
- [ ] No CSP errors when modal opens (check console)
- [ ] Enter credentials and sign in
- [ ] Successfully authenticated
- [ ] Redirected to `/dashboard` after sign-in

**If sign-in fails, note error**:
_______________________________________________

---

### 3. Dashboard & API Connection
- [ ] Dashboard page loads
- [ ] Open DevTools → **Network** tab
- [ ] Clear network log (trash can icon)
- [ ] Refresh page or click "Books" in navigation
- [ ] Look for request to: `api.dev.autoauthor.app/api/v1/books`
- [ ] Request shows **200 OK** or **empty array** response
- [ ] **No 500 errors**
- [ ] **No CORS errors**
- [ ] Response headers include `access-control-allow-origin`

**Network request details**:
- Status Code: _______
- Response: _________________

---

### 4. Create New Book
- [ ] Click "New Book" button or navigate to `/dashboard/new-book`
- [ ] Form displays correctly
- [ ] Fill in:
  - Book Title: "Test Deployment Book"
  - Description: "Testing deployment"
- [ ] Click "Create" or "Submit"
- [ ] Monitor Network tab for POST to `/api/v1/books/`
- [ ] Request includes `Authorization: Bearer ...` header
- [ ] Response is **201 Created** or **200 OK**
- [ ] Redirected to book detail page
- [ ] New book appears in books list

**If creation fails**:
- Status: _______
- Error: _________________

---

### 5. Book Detail & Chapters
- [ ] Click on a book from the list
- [ ] Book detail page loads
- [ ] Table of Contents (TOC) displays
- [ ] Click on a chapter
- [ ] Chapter editor loads
- [ ] Rich text editor is functional (can type)
- [ ] No console errors

---

### 6. Swagger API Documentation
- [ ] Open new tab
- [ ] Navigate to: `https://api.dev.autoauthor.app/docs`
- [ ] Swagger UI interface loads completely
- [ ] **No white/blank page**
- [ ] Check console for errors
- [ ] **No CSP errors blocking resources**
- [ ] Can expand/collapse endpoints
- [ ] FastAPI logo/favicon loads

**If Swagger issues**:
_______________________________________________

---

## Security Checks

### CSP Headers - Frontend
- [ ] Test frontend CSP:
```bash
curl -I https://dev.autoauthor.app | grep content-security-policy
```
- [ ] Includes: `connect-src` with `api.dev.autoauthor.app`
- [ ] Includes: `script-src` with `clerk.accounts.dev`

### CSP Headers - Backend
- [ ] Test backend CSP:
```bash
curl -I https://api.dev.autoauthor.app/docs | grep content-security-policy
```
- [ ] Includes: `script-src` with `cdn.jsdelivr.net`
- [ ] Includes: `style-src` with `cdn.jsdelivr.net`
- [ ] Includes: `img-src` with `fastapi.tiangolo.com`

---

## Performance Check

### Core Web Vitals (Optional)
- [ ] Open https://dev.autoauthor.app
- [ ] Open DevTools → **Lighthouse** tab
- [ ] Click "Analyze page load"
- [ ] Performance score: _______ (target: >80)
- [ ] LCP (Largest Contentful Paint): _______ (target: <2.5s)
- [ ] CLS (Cumulative Layout Shift): _______ (target: <0.1)

---

## Regression Tests

### Critical User Flows
- [ ] **Sign Out → Sign In → Dashboard**
  - [ ] Sign out button works
  - [ ] Sign in again successful
  - [ ] Dashboard loads after sign-in

- [ ] **Create → Edit → Save Book**
  - [ ] Create new book works
  - [ ] Can edit book title/description
  - [ ] Changes save successfully

- [ ] **Generate TOC**
  - [ ] Navigate to book → "Generate TOC"
  - [ ] TOC generation wizard loads
  - [ ] Can complete TOC generation

- [ ] **Chapter Editing**
  - [ ] Open any chapter
  - [ ] Can type in editor
  - [ ] Formatting tools work
  - [ ] Auto-save indicator appears

---

## Final Verification

### No Errors Checklist
- [ ] No CORS errors in any console
- [ ] No CSP violations in any console
- [ ] No 500 errors in Network tab
- [ ] No 401/403 errors on authenticated endpoints
- [ ] All PM2 processes remain **online**
- [ ] Backend logs show no errors during testing

### Functional Completeness
- [ ] User can sign in
- [ ] User can create a book
- [ ] User can view books
- [ ] User can edit chapters
- [ ] API documentation accessible
- [ ] No broken features from previous version

---

## Sign-Off

**All tests passed**: ☐ Yes  ☐ No

**Issues found**:
1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

**Deployment Status**: ☐ Approved  ☐ Needs Fixes

**Tester Signature**: _______________ **Date**: _______________

---

## Quick Troubleshooting

### If you see: "Access blocked by CORS policy"
**Fix**:
```bash
ssh root@47.88.89.175
grep BACKEND_CORS_ORIGINS /opt/auto-author/current/backend/.env
# Should include: "https://dev.autoauthor.app"
# If missing, add it and restart: pm2 restart auto-author-backend
```

### If you see: 500 Internal Server Error
**Check**:
```bash
ssh root@47.88.89.175
pm2 logs auto-author-backend --lines 50 | grep -A 10 "Error\|Traceback"
```
**Common cause**: JWT key format issue - see deployment docs

### If Swagger UI is blank/white
**Check console for**: "refused to load" errors
**Fix**: Backend CSP headers need cdn.jsdelivr.net - see deployment docs

### If frontend can't connect to API
**Check**:
1. Frontend .env has correct API URL: `NEXT_PUBLIC_API_URL=https://api.dev.autoauthor.app/api/v1`
2. Frontend was rebuilt after .env change: `npm run build`
3. PM2 restarted: `pm2 restart auto-author-frontend`

---

## Rollback Procedure

**If critical issues found**:
1. ☐ Document all issues above
2. ☐ Notify deployment team
3. ☐ Execute rollback:
```bash
ssh root@47.88.89.175
cd /opt/auto-author
# Restore from backup tarball if available
tar -xzf backup-[timestamp].tar.gz -C current/
pm2 restart all
```
4. ☐ Verify rollback successful by re-running tests

---

## Notes & Observations

**Additional Comments**:
_______________________________________________
_______________________________________________
_______________________________________________

**Performance Observations**:
_______________________________________________
_______________________________________________

**Recommended Improvements**:
_______________________________________________
_______________________________________________
