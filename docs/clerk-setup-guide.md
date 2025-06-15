# Clerk Authentication Setup Guide

## Required Clerk Credentials

The application needs the following Clerk credentials in your backend `.env` file:

### 1. CLERK_API_KEY
- **Where to find**: Clerk Dashboard → API Keys → Secret keys
- **Format**: `sk_test_...` or `sk_live_...`
- **Purpose**: Server-side API authentication

### 2. CLERK_JWT_PUBLIC_KEY
- **Where to find**: Clerk Dashboard → API Keys → JWT Templates → Default → Public Key
- **Format**: Multi-line RSA public key starting with `-----BEGIN PUBLIC KEY-----`
- **Note**: In the .env file, replace newlines with `\n` (literal backslash-n)
- **Example**:
  ```
  CLERK_JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...\n-----END PUBLIC KEY-----"
  ```

### 3. CLERK_FRONTEND_API
- **Where to find**: Clerk Dashboard → API Keys → Frontend API URL
- **Format**: `clerk.[your-domain].com` or similar
- **Purpose**: Frontend SDK configuration

### 4. CLERK_BACKEND_API
- **Where to find**: Clerk Dashboard → API Keys → Backend API URL
- **Format**: `api.clerk.com` or your custom backend API URL
- **Purpose**: Backend API endpoint

### 5. CLERK_WEBHOOK_SECRET (Optional)
- **Where to find**: Clerk Dashboard → Webhooks → Signing Secret
- **Format**: `whsec_...`
- **Purpose**: Verify webhook signatures (only if using webhooks)

## Quick Setup Steps

1. Log in to your [Clerk Dashboard](https://dashboard.clerk.com/)
2. Select your application
3. Navigate to **API Keys** in the left sidebar
4. Copy the required values:
   - **Secret Key** → `CLERK_API_KEY`
   - **Frontend API URL** → `CLERK_FRONTEND_API`
   - **Backend API URL** → `CLERK_BACKEND_API`
5. Navigate to **JWT Templates** → **Default**
6. Copy the **Public Key** → `CLERK_JWT_PUBLIC_KEY` (remember to escape newlines)

## Example .env Configuration

```env
# Clerk Authentication
CLERK_API_KEY=sk_test_your_secret_key_here
CLERK_JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...\n-----END PUBLIC KEY-----"
CLERK_FRONTEND_API=clerk.your-app.com
CLERK_BACKEND_API=api.clerk.com
CLERK_JWT_ALGORITHM=RS256
CLERK_WEBHOOK_SECRET=whsec_your_webhook_secret_if_using_webhooks
```

## Testing Your Configuration

1. Start the backend server:
   ```bash
   cd backend
   uv run uvicorn app.main:app --reload
   ```

2. If configured correctly, you should see no Clerk-related errors in the startup logs

3. Test authentication by accessing a protected endpoint through the frontend

## Common Issues

1. **JWT Public Key Format**: Make sure to escape newlines with `\n` in the .env file
2. **Wrong Environment**: Ensure you're using test keys for development and live keys for production
3. **CORS Issues**: Add your frontend URL to `BACKEND_CORS_ORIGINS` in config.py if needed

---

*Last Updated: January 2025*