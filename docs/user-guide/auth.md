# Authentication & Registration User Guide

This guide explains how to register, sign in, and manage your account in Auto Author.

## Related Documentation

- [Profile Management Guide](profile-management.md) - Complete guide to managing your profile
- [Session Management](../development/session-management.md) - How sign-in, sign-out and sessions work

## Table of Contents

1. [Registration](#registration)
2. [Sign In](#sign-in)
3. [Account Management](#account-management)
4. [Security Features](#security-features)
5. [Troubleshooting](#troubleshooting)

## Registration

Registration is by email and password only.

### Email Registration

1. Navigate to the **Sign Up** page.
2. Enter your name, email address and a password (at least 8 characters, with an uppercase letter, a lowercase letter and a number).
3. Open the verification link sent to your email. It expires after one hour. Opening it finishes creating your account and signs you in.

The line above the **Sign Up** button says that creating an account means you agree to the [Terms of Service](/terms) and [Privacy Policy](/privacy). We record which version of the Terms you accepted and when.

## Sign In

### Email Sign In

1. Navigate to the **Sign In** page.
2. Enter your email address and password.
3. Click "Sign In".
4. If you've enabled two-factor authentication, enter the verification code.

### Forgot Password

If you forget your password:
1. Click "Forgot password?" on the sign-in page.
2. Enter your email address.
3. Follow the reset instructions sent to your email.
4. Create a new password.

## Account Management

### Profile Settings

Edit your profile at `/profile`:

- Profile picture (JPEG, PNG, WebP or GIF, up to 5 MB)
- First name, last name, display name and bio
- Email and marketing notification toggles

Your email address is shown but cannot be changed there. Change your password under **Settings** → **Security**.

For detailed information on profile management features and options, please refer to our comprehensive [Profile Management Guide](profile-management.md).

### Account Security

Under **Settings** → **Security**:

1. **Two-factor authentication (2FA)**: authenticator-app (TOTP) codes, with backup codes.
2. **Active sessions**: view the devices signed into your account and sign out one or all others.

### Notification Preferences

Under **Settings** → **Notifications** you can switch email notifications, marketing emails, writing reminders, progress updates and backup notifications on or off.

## Security Features

### Two-factor Authentication

To turn on two-factor authentication:
1. Go to **Settings** → **Security**
2. Set up two-factor authentication with an authenticator app
3. Save your backup codes in a secure location

### Account Recovery

If you lose your authenticator:
1. On the verification page, choose "Use a backup code instead"
2. Enter one of the backup codes you saved

If you have lost your backup codes too, email support@autoauthor.app from the address on your account and we will help you regain access. To recover a forgotten password, use "Forgot password?".

### Password Best Practices

- Use a unique, strong password
- Change your password periodically
- Don't reuse passwords from other sites
- Consider using a password manager

## Troubleshooting

### Sign-in Problems

**Email verification not received**:
- Check your spam/junk folder
- Ensure you entered the correct email address
- Sign in with your email and password: a new link is sent each time an unverified account tries to sign in. Links expire after one hour

**Cannot sign in with the correct password**:
- Verify your email address first: an unverified account is refused with "Verify your email address to sign in" and sent a new link
- Use "Forgot password?" to reset the password
- Clear the site's cookies, or try a private window, to rule out a stale session

**Two-factor code rejected or unavailable**:
- Authenticator codes depend on your device clock, so make sure it is set automatically
- On the verification page, choose the backup-code option and enter one of the backup codes you saved when you enabled two-factor authentication

### Signed Out or Redirected to Sign In

Sessions last up to 7 days and are renewed while you use the app. You are sent back to **Sign In** (with a link back to the page you were on) when:

- The session expired, was revoked from another device, or the account was closed. Sign in again.
- Your browser blocks or clears cookies. Allow cookies for the site, then sign in again.

Signing in again is the fix in every case. Resetting your password ends all of your sessions, so every device must sign in again.

### API Authentication Errors

For developers calling the backend directly, with the session cookie:

| Status | Message | Meaning |
|--------|---------|---------|
| 401 | `Not authenticated. Please sign in.` | No valid session cookie was sent |
| 401 | `Invalid session. Please sign in again.` | The session has no user |
| 401 | `User not found. Please sign up again.` | The session outlived its user |
| 401 | `This account is no longer active.` | The account was deactivated or deleted |
| 403 | `Verify your email address to use this account.` | The email address is not verified |
| 503 | `The service is temporarily unavailable. Please try again in a moment.` | The session could not be checked; retry after the `Retry-After` seconds. This does not end your session |

If a signed-in browser gets a 401 from the backend, the app signs it out and redirects to **Sign In**. For cookie and session configuration, see [Session Management](../development/session-management.md).

### Still Need Help?

Contact our support team at support@autoauthor.app.
