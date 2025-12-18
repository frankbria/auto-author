# Environment Variable Refactoring Summary

## Clerk to Better Auth Migration (2025-12-17)

### Removed Clerk Configuration

The following Clerk authentication variables have been removed:

- `CLERK_API_KEY` - Clerk API key (no longer needed)
- `CLERK_PUBLISHABLE_KEY` - Clerk publishable key (no longer needed)
- `CLERK_JWT_PUBLIC_KEY` - Clerk JWT public key for RS256 validation (replaced by HS256)
- `CLERK_FRONTEND_API` - Clerk frontend API endpoint (no longer needed)
- `CLERK_BACKEND_API` - Clerk backend API endpoint (no longer needed)
- `CLERK_SECRET_KEY` - Clerk secret key (no longer needed)
- `CLERK_WEBHOOK_SECRET` - Clerk webhook validation secret (no longer needed)
- `CLERK_JWT_ALGORITHM` - JWT algorithm setting (was "RS256", now fixed to "HS256")

**Associated Code Changes**:
- Removed `clerk_jwt_public_key_pem` property from `Settings` class in `app/core/config.py`
- Removed all Clerk authentication imports and functions

### Added Better Auth Configuration

The following better-auth authentication variables have been added:

- `BETTER_AUTH_SECRET` - Shared secret key for JWT signing and verification with HS256
  - Purpose: Used by both frontend (Node.js) and backend (Python) for HMAC-SHA256 JWT operations
  - Generation: `openssl rand -base64 32`
  - **CRITICAL**: Must be identical between frontend and backend environments

- `BETTER_AUTH_URL` - Base URL of the application
  - Purpose: Used for constructing callback URLs and CORS validation
  - Example: `http://localhost:3000` (development) or `https://autoauthor.app` (production)

- `BETTER_AUTH_ISSUER` - JWT issuer identifier
  - Purpose: Used in JWT validation to verify token source
  - Default: `better-auth`

- `JWT_ALGORITHM` - JWT signing algorithm (changed from config field to hardcoded)
  - Changed from: `CLERK_JWT_ALGORITHM="RS256"` (asymmetric RSA)
  - Changed to: `JWT_ALGORITHM="HS256"` (symmetric HMAC-SHA256)
  - Impact: Simplified key management - uses single shared secret instead of public/private key pair

**Associated Code Changes**:
- Updated `Settings` class in `app/core/config.py` with new better-auth fields
- Updated `.env.example` with new better-auth variables and instructions
- Security module will validate JWT using HS256 with `BETTER_AUTH_SECRET`

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

## JWT Algorithm Changes

**Before (Clerk)**:
- Algorithm: RS256 (RSA, asymmetric)
- Key Management: Public key distributed, private key kept on Clerk's servers
- Validation: Verify using Clerk's JWKS endpoint

**After (Better Auth)**:
- Algorithm: HS256 (HMAC-SHA256, symmetric)
- Key Management: Single shared secret between frontend and backend
- Validation: Direct HMAC verification using `BETTER_AUTH_SECRET`

This simplification allows self-hosted authentication without external API dependencies.

## Impact Summary

| Aspect | Clerk | Better Auth |
|--------|-------|------------|
| Key Type | Asymmetric (RS256) | Symmetric (HS256) |
| Secrets Required | 7+ variables | 3 variables |
| Complexity | External JWKS + webhooks | Single shared secret |
| Self-Hosted | No | Yes |
| Configuration Time | Higher | Lower |