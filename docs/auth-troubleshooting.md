# Authentication Troubleshooting Guide

This guide helps resolve common authentication issues in Auto Author.

## Table of Contents

1. [Common Login Issues](#common-login-issues)
2. [Token and Session Problems](#token-and-session-problems)
3. [API Authentication Errors](#api-authentication-errors)
4. [Social Login Troubleshooting](#social-login-troubleshooting)
5. [Multi-Factor Authentication Issues](#multi-factor-authentication-issues)
6. [Environment Variable Misconfiguration](#environment-variable-misconfiguration)
7. [Developer Tools](#developer-tools)

## Common Login Issues

### Cannot Log In with Correct Credentials

**Symptoms:**
- Error messages despite entering correct email/password
- "Invalid credentials" errors

**Solutions:**
1. **Reset Password**: Use the "Forgot Password" functionality
2. **Check Email Verification**: Ensure your email is verified
3. **Clear Browser Cache**: Clear cookies and cached data
4. **Check Caps Lock**: Ensure caps lock is disabled
5. **Try Incognito Mode**: Test login in a private/incognito window

### Session Expires Too Quickly

**Symptoms:**
- Frequent logouts while actively using the application
- Need to log in again after short periods

**Solutions:**
1. **Enable "Remember Me"**: Check the "Remember Me" box when logging in
2. **Check Device Time**: Ensure your device clock is synchronized correctly
3. **Browser Settings**: Make sure cookies are enabled and not cleared on exit
4. **Network Issues**: Stable internet connection is required for session maintenance

### Cannot Access Protected Routes

**Symptoms:**
- Redirected to login despite being logged in
- "Unauthorized" errors when accessing certain pages

**Solutions:**
1. **Re-authenticate**: Log out and log back in completely
2. **Check Permissions**: Ensure your account has necessary permissions
3. **Session Verification**: Check if your session is valid (look for auth indicators)
4. **Clear React State**: Try hard refreshing the page (Ctrl+F5)

## Token and Session Problems

### JWT Verification Failures

**Symptoms:**
- API errors with "token verification failed" messages
- Backend console logs showing JWT validation errors

**Solutions:**
1. **Check Clock Sync**: Server and Clerk times must be synchronized
2. **Public Key Issues**: Ensure CLERK_JWT_PUBLIC_KEY is correctly set
3. **Token Expiration**: Check if tokens are expired and need refresh

### Session Recovery Failures

**Symptoms:**
- Application doesn't remember your login between visits
- "session not found" errors in console

**Solutions:**
1. **Browser Storage**: Check if cookies/localStorage are being cleared
2. **Session Duration**: Verify session durations in Clerk dashboard
3. **Domain Issues**: Ensure cookies are set for the correct domain

## API Authentication Errors

### 401 Unauthorized Errors

**Symptoms:**
- API requests fail with 401 status code
- Console errors about missing or invalid authentication

**Solutions:**
1. **Token Inclusion**: Ensure `Authorization` header is present with `Bearer` token
2. **Token Format**: Verify token follows the correct format
3. **Token Expiration**: Check if token has expired and needs refreshing
4. **Permissions**: Verify user has required roles for the endpoint

### 403 Forbidden Errors

**Symptoms:**
- API requests fail with 403 status code despite valid authentication
- "Insufficient permissions" messages

**Solutions:**
1. **User Roles**: Check user's assigned roles in Clerk dashboard
2. **Permission Mapping**: Ensure roles map correctly to required permissions
3. **Resource Ownership**: Verify user has access to the requested resource

## Social Login Troubleshooting

### Social Provider Connection Failures

**Symptoms:**
- Social login buttons lead to error pages
- "Could not connect to provider" errors

**Solutions:**
1. **Provider Status**: Check if the social provider's services are operational
2. **OAuth Configuration**: Verify OAuth credentials and callback URLs in Clerk
3. **Allowed Domains**: Ensure your domain is allowed for the social provider
4. **Popup Blockers**: Disable popup blockers that interfere with oauth flow

### Account Linking Issues

**Symptoms:**
- "Email already in use" when trying to use social login
- Unable to connect existing account to social provider

**Solutions:**
1. **Sign In First**: Sign in with existing credentials, then link accounts in profile
2. **Matching Emails**: Ensure email addresses match between accounts
3. **Provider Settings**: Check if the provider allows email access

## Multi-Factor Authentication Issues

### Cannot Receive MFA Codes

**Symptoms:**
- MFA codes not arriving via email or SMS
- Verification step fails

**Solutions:**
1. **Check Contact Info**: Verify phone number or email is correct
2. **Spam Folder**: Check spam/junk folder for email codes
3. **Alternative Method**: Use backup verification method if configured
4. **Carrier Issues**: Some carriers may block automated SMS messages

### Locked Out Due to MFA

**Symptoms:**
- Unable to pass MFA verification despite multiple attempts
- Account access blocked after failed attempts

**Solutions:**
1. **Recovery Codes**: Use backup recovery codes if previously saved
2. **Support Contact**: Contact support with identity verification information
3. **Cooling Period**: Some lockouts resolve automatically after a time period

## Environment Variable Misconfiguration

**Symptoms:**
- Authentication works locally but fails in production
- Inconsistent auth behavior across environments

**Solutions:**
1. **Environment Check**: Verify all required env variables are set correctly
2. **Key Format**: Ensure keys are formatted properly (no extra quotes or spaces)
3. **Instance Matching**: Make sure frontend and backend use matching Clerk instances
4. **Development vs Production**: Confirm you're using the correct instance for environment

## Developer Tools

### Debugging Authentication Issues

**Browser Tools:**
1. **Network Tab**: Inspect authentication requests and responses
   - Look for 401/403 status codes
   - Check if tokens are included in requests
2. **Application Tab**: Examine stored tokens
   - Check localStorage for Clerk session data
   - Verify cookie values and expiration

**Backend Logs:**
1. **Token Verification**: Look for JWT verification failures
2. **Session Validation**: Check session lookup errors
3. **Permission Checks**: Find role/permission evaluation failures

### Common Error Codes

| Error Code | Description | Solution |
|------------|-------------|----------|
| `auth/invalid-credential` | Invalid email/password | Verify credentials or reset password |
| `auth/user-not-found` | Email not registered | Check email or register new account |
| `auth/too-many-requests` | Rate limiting applied | Wait before retrying or reset password |
| `auth/invalid-token` | JWT verification failed | Re-authenticate or check clock sync |
| `auth/session-expired` | Active session timed out | Log in again |
| `auth/missing-permissions` | User lacks required access | Request appropriate permissions |

For persistent issues not covered in this guide, please contact support with:
1. Your username/email
2. Time and date of the issue
3. Specific error messages
4. Browser and device information
