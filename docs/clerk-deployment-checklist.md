# Clerk Deployment Checklist

This checklist ensures that your Clerk authentication is properly configured for production deployment of Auto Author.

## Prerequisites

- [ ] Clerk account created at [clerk.dev](https://clerk.dev)
- [ ] Production application instance created in Clerk dashboard
- [ ] Domain configured in DNS with proper records
- [ ] SSL certificate configured for your domain

## Environment Variables

### Frontend (Next.js) Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Public key from Clerk dashboard | `pk_live_****` |
| `CLERK_SECRET_KEY` | Secret key from Clerk dashboard (keep secure) | `sk_live_****` |
| `NEXT_PUBLIC_CLERK_SIGN_IN_URL` | Path to sign in page | `/sign-in` |
| `NEXT_PUBLIC_CLERK_SIGN_UP_URL` | Path to sign up page | `/sign-up` |
| `NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL` | Redirect path after sign in | `/dashboard` |
| `NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL` | Redirect path after sign up | `/dashboard` |

### Backend (FastAPI) Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `CLERK_API_KEY` | API key from Clerk dashboard (keep secure) | `sk_live_****` |
| `CLERK_JWT_PUBLIC_KEY` | JWKS public key for verification | `-----BEGIN PUBLIC KEY-----\n...` |
| `CLERK_FRONTEND_API` | Frontend API instance | `clerk.yourdomain.com` |
| `CLERK_JWT_ALGORITHM` | JWT signing algorithm | `RS256` |
| `CLERK_WEBHOOK_SECRET` | Webhook signing secret | `whsec_****` |

## Configuration Steps

### 1. Clerk Dashboard Setup

- [ ] **Authentication methods**: Configure which methods to enable
  - Email/password
  - Social providers (Google, GitHub, etc.)
  - Phone number authentication
  
- [ ] **Domain configuration**:
  - Add your application domain
  - Configure redirect URLs
  
- [ ] **Appearance customization**:
  - Configure theme and branding
  - Customize component appearance to match your app
  
- [ ] **Email templates**:
  - Customize verification emails
  - Set up password reset templates
  - Configure email sender information
  
- [ ] **Session management**:
  - Set session duration
  - Configure session revocation policies
  
- [ ] **Webhooks**:
  - Configure webhook endpoint (`https://your-api.com/api/v1/webhooks/clerk`)
  - Enable specific webhook events (user.created, user.updated, etc.)
  - Copy webhook signing secret to environment variable

### 2. Frontend Deployment

- [ ] **Environment variables**:
  - Add all Clerk environment variables to production environment
  - Verify variables are loaded correctly in the app
  
- [ ] **Build and deployment**:
  - Ensure Clerk SDK is included in production build
  - Check for any client/server hydration issues
  - Verify authentication components render correctly
  
- [ ] **Routing configuration**:
  - Confirm middleware is correctly protecting routes
  - Test public vs. authenticated route access

### 3. Backend Deployment

- [ ] **Environment variables**:
  - Add all Clerk environment variables to backend environment
  - Ensure JWT verification is using correct public key
  
- [ ] **Webhook verification**:
  - Implement webhook signature verification
  - Test webhook handling with test events
  
- [ ] **API authentication**:
  - Verify token validation works correctly
  - Test protected API endpoints
  - Confirm role-based access control functions

### 4. Testing Checklist

- [ ] **Registration flows**:
  - Email registration and verification
  - Social login connections
  - Profile completion
  
- [ ] **Authentication flows**:
  - Sign in with email/password
  - Sign in with social providers
  - Password reset functionality
  - Multi-factor authentication
  
- [ ] **Session management**:
  - Session persistence across page refreshes
  - Proper session expiration
  - Sign out functionality (all devices)
  
- [ ] **API authentication**:
  - Protected routes require authentication
  - JWT tokens are correctly validated
  - Role-based permissions work as expected
  
- [ ] **User management**:
  - User creation in database after registration
  - User data updates synchronize correctly
  - Account deletion properly handles data

## Security Considerations

- [ ] Use environment variables for all sensitive keys and secrets
- [ ] Never expose `CLERK_SECRET_KEY` or `CLERK_API_KEY` in client-side code
- [ ] Implement proper CORS policies on your backend
- [ ] Set appropriate cookie security options (Secure, HttpOnly, SameSite)
- [ ] Regularly rotate API keys and webhook secrets
- [ ] Monitor authentication logs for suspicious activity
- [ ] Configure rate limiting for authentication endpoints

## Monitoring & Maintenance

- [ ] Set up monitoring for authentication failures
- [ ] Configure alerts for suspicious activity
- [ ] Create a process for key rotation
- [ ] Document procedures for handling authentication issues

## Additional Resources

- [Clerk Production Deployment Guide](https://clerk.dev/docs/deployments/overview)
- [Clerk Security Best Practices](https://clerk.dev/docs/security/overview)
- [JWT Authentication Documentation](https://clerk.dev/docs/backend/jwt)
