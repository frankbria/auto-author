# Issue #54 Testing Options

## Problem
Staging server requires real Better-auth authentication (no BYPASS_AUTH).
This means automated Playwright tests need actual user credentials.

## Option 1: Test Locally with BYPASS_AUTH (RECOMMENDED)

**Pros**:
- Fast (no network latency)
- No auth complexity
- Same codebase as staging
- Can verify functionality immediately

**Cons**:
- Tests local deployment, not actual staging
- Database might have different data

**How to Run**:
```bash
cd frontend

# Set environment for local E2E test
export BASE_URL=http://localhost:3000
export BYPASS_AUTH=true
export NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# Start local backend (in separate terminal)
cd ../backend && uv run uvicorn app.main:app --reload

# Start local frontend (in separate terminal)
cd frontend && npm run dev

# Run Issue #54 test
npx playwright test staging-issue-54-verification --project=chromium --headed
```

**Result**: Verifies question persistence logic works correctly

---

## Option 2: Test Against Staging with Real Auth

**Pros**:
- Tests actual production environment
- Validates staging deployment
- Real data persistence

**Cons**:
- Requires test user credentials
- More complex test setup
- Slower (network requests)

**Requirements**:
1. Create test user on staging: https://dev.autoauthor.app
2. Store credentials securely
3. Update test to handle login flow

**Implementation**: Need to add Better-auth login flow to test

---

## Option 3: Enable BYPASS_AUTH on Staging Temporarily

**Pros**:
- Tests actual staging environment
- No auth complexity in test

**Cons**:
- Security risk (must remember to disable after)
- Requires SSH access and restart

**How to Enable** (TEMPORARY ONLY):
```bash
ssh root@dev.autoauthor.app
cd /opt/auto-author/current/backend
echo "BYPASS_AUTH=true" >> .env
pm2 restart auto-author-backend

cd /opt/auto-author/current/frontend
# Add to next start command or .env file
pm2 restart auto-author-frontend
```

**⚠️ WARNING**: Must disable BYPASS_AUTH after testing!

---

## Recommendation

**Use Option 1 (Local Testing)** because:

1. ✅ Same code as staging (tests the feature, not the deployment)
2. ✅ Fast feedback (<5 minutes)
3. ✅ No security risks
4. ✅ Can run immediately

**What It Verifies**:
- Question answer persistence (the core Issue #54 concern)
- Database save/retrieve cycle
- Frontend state management

**What It Doesn't Verify**:
- Staging deployment specifics
- Network conditions
- MongoDB Atlas performance

**Confidence Level**: 95%
- If local test passes → Feature works, staging probably works too
- If local test fails → Definite blocker regardless of deployment

---

## Decision Matrix

| Scenario | Recommended Option |
|----------|-------------------|
| Quick verification needed | Option 1 (Local) |
| Must validate staging deployment | Option 2 (Real Auth) |
| Have SSH access, need quick staging test | Option 3 (Temporary Bypass) |
| CI/CD pipeline testing | Option 2 (Real Auth) |

---

## Next Steps

**Immediate** (5 minutes):
1. Choose option
2. Set up environment
3. Run test

**After Test**:
- If PASS → Close Issue #54 as verified
- If FAIL → Fix persistence bug (P0 blocker)
