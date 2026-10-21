# Environment Variable Refactoring Summary

## Removed settings (2026-10-14)

Issue #851: **BETTER_AUTH_ISSUER** and **JWT_ALGORITHM** are no longer read. Nothing used either, so a value left in an `.env` is ignored and can be deleted. Compose's **CORS_ORIGINS** was never read: **BACKEND_CORS_ORIGINS** is the variable. The sections below describe these settings as they were.

## Stripe Tax (2026-10-09)

Issue #783: **STRIPE_AUTOMATIC_TAX** (bool, default `false`) sets `automatic_tax.enabled` on Checkout Sessions. Set it to `true` only after Stripe Tax is activated in the Dashboard (origin address and registrations), or Stripe rejects every checkout. A billing address and tax IDs are collected either way.

## AI Provider and Models (2026-10-09)

Issue #917: point the OpenAI client at any OpenAI-compatible endpoint and choose models per flow class. All are optional, and with none set the requests are unchanged.

- **AI_BASE_URL**: an OpenAI-compatible base URL (`…/v1`). Empty means api.openai.com.
- **AI_API_KEY**: takes precedence over `OPENAI_API_KEY`, and is the only key used when `AI_BASE_URL` is set.
- **AI_MODEL_DEFAULT** (`gpt-4`) / **AI_MODEL_LONG_OUTPUT** (`gpt-4o`, drafts and TOC).
- **AI_MAX_OUTPUT_TOKENS_DEFAULT** (4000) / **AI_MAX_OUTPUT_TOKENS_LONG** (8000): caps on each class's `max_tokens`.

Details: `docs/STAGING-DEPLOYMENT.md` → "AI provider settings (#917)".

## Stripe Checkout (2026-07-09)

### Overview

Issue #221: `POST /api/v1/billing/checkout` creates a Stripe Checkout session for upgrading `free` → `pro`. The plan flip stays webhook-only (#220); checkout only establishes the customer/subscription linkage.

### Changes

- **STRIPE_SECRET_KEY** (`app/core/config.py`): the Stripe API secret key (`sk_test_...`/`sk_live_...`). Unset ⇒ checkout fails closed with 503 and never calls Stripe. This closes the "deliberately omitted until #221" note from the webhook entry below.

### Test Coverage

`tests/test_api/test_billing_checkout.py` (real Mongo; Stripe SDK boundary stubbed).

## Stripe Webhook Integration (2026-07-09)

### Overview

Issue #220: `POST /api/v1/webhooks/stripe` verifies Stripe webhook payloads against the raw request body (HMAC) and syncs `customer.subscription.*` events to the user's `plan`.

### Changes

- **STRIPE_WEBHOOK_SECRET** (`app/core/config.py`): the Stripe webhook signing secret (`whsec_...`). Unset ⇒ the endpoint fails closed with 503 and never processes a payload.
- **STRIPE_PRICE_ID_PRO** (`app/core/config.py`): the Stripe price id mapped to the `pro` plan by `app/core/entitlements.py::resolve_plan_for_price`; unknown/missing prices resolve to `free`.
- **Deliberately omitted**: no `STRIPE_SECRET_KEY` yet — nothing calls the Stripe API until checkout (#221).

### Test Coverage

`tests/test_api/test_stripe_webhook.py` (real HMAC signatures + real Mongo) and `tests/test_core/test_entitlements.py::TestStripePricePlanResolution`.

## Security Enhancement: BYPASS_AUTH Production Protection (2025-12-18)

### Overview

Added production environment validation for `BYPASS_AUTH` to prevent accidental exposure of authentication bypass in production deployments.

### Changes

- **Pydantic Validator**: Added `@field_validator('BYPASS_AUTH')` in `app/core/config.py` that raises `ValueError` if `BYPASS_AUTH=true` when `NODE_ENV=production`
- **Startup Validation**: Added `validate_production_security()` function in `app/main.py` that provides fail-fast behavior with clear error messages
- **Deployment Workflow**: Added security check step in `.github/workflows/deploy-staging.yml` to detect if `BYPASS_AUTH` secret is accidentally configured
- **Documentation**: Updated `.env.example` with clear warnings about production usage

### Validation Behavior

Since #307, `BYPASS_AUTH=true` takes effect only together with
`E2E_ALLOW_BYPASS=1` (exact value) outside production:

| Environment | BYPASS_AUTH=true | BYPASS_AUTH=true + E2E_ALLOW_BYPASS=1 | BYPASS_AUTH=false |
|-------------|------------------|----------------------------------------|-------------------|
| `production` | ❌ Startup blocked | ❌ Startup blocked (no exemption) | ✅ Normal operation |
| `staging` | ⚠️ Ignored (coerced off + warning) | ✅ Allowed (manual runs; the deploy workflow rejects the BYPASS_AUTH secret regardless) | ✅ Normal operation |
| `development` | ⚠️ Ignored (coerced off + warning) | ✅ Allowed | ✅ Normal operation |
| `test` | ⚠️ Ignored (coerced off + warning) | ✅ Allowed | ✅ Normal operation |
| (not set) | ⚠️ Ignored (coerced off + warning) | ✅ Allowed | ✅ Normal operation |

### Error Messages

When `BYPASS_AUTH=true` in production:

1. **Config validation error**: "FATAL SECURITY ERROR: BYPASS_AUTH cannot be enabled in production environment. This would allow unauthorized access to all user data and features."

2. **Startup error**: "Application startup blocked: BYPASS_AUTH is enabled in production environment."

### Test Coverage

- `tests/test_core/test_security.py`: `TestProductionSecurityValidation` class with 6 test cases
- `tests/test_main.py`: `TestStartupSecurityValidation` class with 5 test cases

---

## Clerk to Better Auth Migration (2025-12-17)

### Removed Clerk Configuration

The following Clerk authentication variables have been removed:

- `CLERK_API_KEY` - Clerk API key (no longer needed)
- `CLERK_PUBLISHABLE_KEY` - Clerk publishable key (no longer needed)
- `CLERK_JWT_PUBLIC_KEY` - Clerk JWT public key for RS256 validation (no longer needed)
- `CLERK_FRONTEND_API` - Clerk frontend API endpoint (no longer needed)
- `CLERK_BACKEND_API` - Clerk backend API endpoint (no longer needed)
- `CLERK_SECRET_KEY` - Clerk secret key (no longer needed)
- `CLERK_WEBHOOK_SECRET` - Clerk webhook validation secret (no longer needed)
- `CLERK_JWT_ALGORITHM` - JWT algorithm setting (no longer needed)

**Associated Code Changes**:
- Removed `clerk_jwt_public_key_pem` property from `Settings` class in `app/core/config.py`
- Removed all Clerk authentication imports and functions

### Added Better Auth Configuration

The following better-auth authentication variables have been added:

- `BETTER_AUTH_SECRET` - better-auth's secret for signing its session cookies
  - Purpose: Used by both frontend (Node.js) and backend (Python); the backend checks the session cookie's signature with it
  - Generation: `python -c 'import secrets; print(secrets.token_urlsafe(64))'`
  - **CRITICAL**: Must be identical between frontend and backend environments

- `BETTER_AUTH_URL` - Base URL of the application
  - Purpose: Used for constructing callback URLs and CORS validation
  - Example: `http://localhost:3000` (development) or `https://autoauthor.app` (production)

**Associated Code Changes**:
- Updated `Settings` class in `app/core/config.py` with new better-auth fields
- Updated `.env.example` with new better-auth variables and instructions
- The security module looks the session up in MongoDB by cookie and checks the cookie signature with `BETTER_AUTH_SECRET`

## Previous OpenAI Migration (2025-XX-XX)

### Changed Configuration

1. **Updated Configuration** (`app/core/config.py`):
   - Changed `OPENAI_API_KEY` to `OPENAI_AUTOAUTHOR_API_KEY`

2. **Updated AI Service** (`app/services/ai_service.py`):
   - Updated the AI service initialization to use `settings.OPENAI_AUTOAUTHOR_API_KEY`

3. **Updated Environment Files**:
   - `.env.example`: Changed `OPENAI_API_KEY` to `OPENAI_AUTOAUTHOR_API_KEY`
   - `.env.test`: Changed `OPENAI_API_KEY` to `OPENAI_AUTOAUTHOR_API_KEY`

4. **Updated Test Files**:
   - `test_config.py`: Changed environment variable name
   - `test_services_isolated.py`: Changed environment variable name
   - `test_services_summary.py`: Changed environment variable name
   - `run_unit_tests.py`: Changed environment variable name

## Migration Steps

### For Local Development

1. Generate a new better-auth secret:
   ```bash
   openssl rand -base64 32
   ```

2. Update your `.env` file in the backend directory:
   ```
   BETTER_AUTH_SECRET=<your-generated-secret>
   BETTER_AUTH_URL=http://localhost:3000
   BETTER_AUTH_ISSUER=better-auth
   ```

3. Remove all Clerk-related variables from your `.env` file

4. Ensure the frontend has the same `BETTER_AUTH_SECRET` value

5. Restart your backend server

### For Production Deployment

1. Generate a secure secret for production:
   ```bash
   openssl rand -base64 32
   ```

2. Set environment variables on your deployment platform:
   - `BETTER_AUTH_SECRET` - Your generated secret
   - `BETTER_AUTH_URL` - Your production URL (e.g., https://autoauthor.app)
   - `BETTER_AUTH_ISSUER` - better-auth (or your custom issuer)

3. Ensure frontend and backend use the same `BETTER_AUTH_SECRET`

4. Remove all Clerk environment variables from deployment

## Authentication Changes

**Before (Clerk)**: the backend verified a Clerk JWT (RS256) against Clerk's JWKS endpoint.

**After (Better Auth)**: the backend reads the better-auth session cookie, checks its signature with `BETTER_AUTH_SECRET`, and looks the session up in MongoDB. There is no JWT.

This allows self-hosted authentication without external API dependencies.

## Impact Summary

| Aspect | Clerk | Better Auth |
|--------|-------|------------|
| Credential | Clerk JWT (RS256) | Session cookie signed with a shared secret |
| Secrets Required | 7+ variables | 3 variables |
| Complexity | External JWKS + webhooks | Single shared secret |
| Self-Hosted | No | Yes |
| Configuration Time | Higher | Lower |