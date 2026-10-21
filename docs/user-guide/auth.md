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

Auto Author provides a straightforward registration process with multiple options.

### Email Registration

1. Navigate to the **Sign Up** page.
2. Enter your email address.
3. Create a secure password (at least 8 characters, including numbers and special characters).
4. Complete the verification process by clicking the link sent to your email.
5. Fill in your profile information (name, etc.).
6. You'll be redirected to the dashboard after successful registration.

The line above the **Sign Up** button says that creating an account means you agree to the [Terms of Service](/terms) and [Privacy Policy](/privacy). We record which version of the Terms you accepted and when.

### Social Login Options

You can also register using your existing accounts:

- **Google**: Click the Google button on the sign-up page
- **GitHub**: Click the GitHub button on the sign-up page
- **Microsoft**: Click the Microsoft button on the sign-up page

When using social login, you'll be asked to grant Auto Author permission to access basic profile information. We only use this information to create your account and never post on your behalf.

### Profile Setup

After registration, you'll be prompted to complete your profile:
- Add a profile picture (optional)
- Verify your name
- Set your writing preferences (optional)

## Sign In

### Email Sign In

1. Navigate to the **Sign In** page.
2. Enter your email address and password.
3. Click "Sign In".
4. If you've enabled two-factor authentication, enter the verification code.

### Social Login

Click on the social provider button you used during registration. You'll be redirected to that provider's authentication page and then back to Auto Author after successful authentication.

### "Remember Me" Option

Check the "Remember me" option during sign-in to stay logged in on your device. For security reasons, some actions may still require re-authentication.

### Forgot Password

If you forget your password:
1. Click "Forgot password?" on the sign-in page.
2. Enter your email address.
3. Follow the reset instructions sent to your email.
4. Create a new password.

## Account Management

### Profile Settings

Access profile settings through the user menu in the top-right corner:

1. Click your profile picture or initials.
2. Select "Profile" from the dropdown menu.
3. Update your information:
   - Profile picture
   - Name
   - Bio
   - Email address (requires verification)
   - Password

For detailed information on profile management features and options, please refer to our comprehensive [Profile Management Guide](profile-management.md).

### Account Security

Enhance your account security:

1. **Two-factor authentication (2FA)**:
   - Enable in Security Settings
   - Choose between SMS, authenticator app, or email verification
   
2. **Connected devices**:
   - View all devices signed into your account
   - Sign out from specific devices remotely
   
3. **Login history**:
   - Review recent login attempts
   - Verify if any unauthorized access attempts occurred

### Email Preferences

Manage your email settings:

1. Go to the Settings page.
2. Navigate to the "Notifications" tab.
3. Configure which emails you want to receive:
   - Account notifications
   - Product updates
   - Marketing communications

## Security Features

### Multi-factor Authentication

For enhanced security, enable multi-factor authentication:
1. Go to Security Settings
2. Select "Enable Two-Factor Authentication"
3. Choose your preferred method:
   - Authenticator app (recommended)
   - SMS verification
   - Email verification
4. Follow the setup instructions
5. Save your backup codes in a secure location

### Account Recovery

If you lose access to your authentication method:
1. Click "Need help?" on the sign-in page
2. Select "Can't access my account"
3. Follow the recovery steps
4. Use backup codes if available

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

**Social login issues**:
- Ensure pop-ups aren't blocked by your browser
- Check that your social account email matches your Auto Author account
- Try signing in with email and password instead

**Locked account**:
- After multiple failed attempts, your account may be temporarily locked
- Wait 30 minutes before trying again
- Use the "Forgot password" option to reset if needed

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

Contact our support team:
- Email: support@auto-author.com
- In-app: Click "Help" in the footer menu
