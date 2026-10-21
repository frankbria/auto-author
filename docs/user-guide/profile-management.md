# Profile Management Documentation

This guide provides comprehensive information about the profile management features in Auto Author, including user options, editing procedures, API endpoints, troubleshooting, and security considerations.

## Table of Contents

1. [Profile Management Features](#profile-management-features)
2. [User Guide for Profile Editing](#user-guide-for-profile-editing)
3. [API Endpoints for Profile Operations](#api-endpoints-for-profile-operations)
4. [Frontend Components](#frontend-components)
5. [Troubleshooting Common Profile Issues](#troubleshooting-common-profile-issues)
6. [Security Considerations](#security-considerations)

---

## Related Documentation

- [API Profile Endpoints](../api/profile.md) - Detailed API documentation for profile operations
- [Authentication User Guide](auth.md) - Sign-in, sessions and auth troubleshooting
- [Session Management](../development/session-management.md) - How sessions and cookies work

---

## Profile Management Features

Your sign-in identity (email, password, two-factor authentication) is handled by better-auth. Your profile (names, bio, picture, preferences) is stored in Auto Author's own database.

### Core Features

- **Basic Information Management**: Edit first name, last name, and bio
- **Profile Picture Management**: Upload and update profile pictures
- **User Preferences**: Customize application appearance and notification settings
- **Account Management**: Options for account deletion
- **Data export**: Download your data as a JSON file

### User Preferences Options

Auto Author supports the following user preferences:

| Preference | Description | Default Value |
|------------|-------------|---------------|
| Theme | UI color scheme (light/dark/system) | Dark |
| Email Notifications | Receive important updates | Enabled |
| Marketing Emails | Receive promotional content | Disabled |

---

## User Guide for Profile Editing

### Accessing Your Profile

1. **Navigate to Profile**: Click your avatar in the top-right corner of any page, then select "Profile" from the dropdown menu
2. **Direct Access**: Go directly to `/profile` in your browser

### Editing Basic Information

1. **Name Fields**: Update your first name, last name and display name in the corresponding fields
2. **Bio**: Share information about yourself in the bio text area
3. **Email**: Your email address is shown but cannot be changed on this page

Click **Save Changes** to apply your edits.

### Managing Your Profile Picture

1. **View Current Picture**: Your profile image appears at the top of the profile page
2. **Change Picture**:
   - Click the edit icon (pencil) on the profile picture
   - Select a JPEG, PNG, WebP or GIF image of up to 5 MB
   - The image is uploaded and displayed

### Setting Preferences

The profile page has two notification toggles: "Email notifications" and "Marketing emails". Theme and the other preferences are on the **Settings** page.

### Account Management

In the "Account Settings" section, you can:

1. **Change Password**: use **Settings** → **Security** → Change Password
2. **Download my data**: Click "Download my data" to save a JSON file with your profile, your books and the questions, answers and ratings in them
3. **Delete Account**:
   - Click "Delete Account"
   - Confirm by typing your email address in the prompt
   - Click "Deactivate account and delete books" in the confirmation dialog

> ⚠️ **Warning**: Your books are deleted at once and cannot be recovered. The account is deactivated; its account and billing record is kept for 18 months for complaints and payment disputes, then erased. Email support to have it erased sooner.

---

## API Endpoints for Profile Operations

Auto Author provides several API endpoints for profile management. All endpoints require a signed-in session: the API reads the better-auth session cookie, not a bearer token.

### Base URL

```
https://api.dev.autoauthor.app/api/v1
```

For local development:

```
http://localhost:8000/api/v1
```

### Current User Profile

**Endpoint**: `GET /users/me`

**Description**: Retrieves the current authenticated user's profile information

**Authentication**: Required

**Response Format**:
```json
{
  "id": "string",
  "auth_id": "string",
  "email": "user@example.com",
  "first_name": "string",
  "last_name": "string",
  "display_name": "string",
  "avatar_url": "string",
  "bio": "string",
  "role": "user",
  "created_at": "2025-05-01T12:00:00Z",
  "updated_at": "2025-05-17T12:00:00Z",
  "preferences": {
    "theme": "dark",
    "email_notifications": true,
    "marketing_emails": false
  }
}
```

**Status Codes**:
- `200 OK`: Profile retrieved successfully
- `401 Unauthorized`: No valid session cookie
- `500 Internal Server Error`: Server-side error

### Update Profile

**Endpoint**: `PATCH /users/me`

**Description**: Updates the current user's profile information

**Authentication**: Required

**Rate Limiting**: 5 requests per minute

**Request Format**:
```json
{
  "first_name": "string",
  "last_name": "string",
  "bio": "string",
  "preferences": {
    "theme": "dark",
    "email_notifications": true,
    "marketing_emails": false
  }
}
```

**Response Format**: Same as GET /users/me

**Status Codes**:
- `200 OK`: Profile updated successfully
- `400 Bad Request`: Invalid data format
- `401 Unauthorized`: No valid session cookie
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server-side error

### Delete Account

**Endpoint**: `DELETE /users/me`

**Description**: Deletes the current user's books and deactivates the account; the account and billing record is kept for 18 months (see [API Profile Endpoints](../api/profile.md))

**Authentication**: Required

**Rate Limiting**: 3 requests per 5 minutes

**Response Format**:
```json
{
  "message": "Account deactivated"
}
```

**Status Codes**:
- `200 OK`: Account deactivated
- `401 Unauthorized`: No valid session cookie
- `404 Not Found`: User not found or already deleted
- `429 Too Many Requests`: Rate limit exceeded

---

## Frontend Components

For developers. Profile editing is split into a page, an API hook and a form schema.

- **Profile page** (`frontend/src/app/profile/page.tsx`, route `/profile`, sign-in required): loads the profile, edits it with a form, and handles notification preferences and account deletion.
- **`useProfileApi`** (`frontend/src/hooks/useProfileApi.ts`): cookie-authenticated calls to the profile API, with three methods: `getUserProfile()` (`GET /users/me`), `updateUserProfile(data)` (`PATCH /users/me`) and `deleteUserAccount()` (`DELETE /users/me`).
- **`ProfilePictureUpload`** (`frontend/src/components/profile/ProfilePictureUpload.tsx`): shows the avatar and uploads a new one with `POST /users/me/avatar`. Uploads do not go through `useProfileApi`.

The form validates with Zod:

| Field | Rule |
|-------|------|
| First name, last name | up to 50 characters each |
| Display name | up to 100 characters |
| Bio | up to 1000 characters (a counter is shown) |
| Email notifications, marketing emails | on/off |

Data flow: the page reads the session, calls `getUserProfile()` and fills the form. Saving validates, calls `updateUserProfile()` with the full `preferences` object merged with the edited fields (the backend replaces the whole preferences subdocument), and shows a "Profile updated" toast. Saving is disabled until the profile has loaded, so a failed load cannot overwrite stored preferences. Theme is owned by the Settings page, not the profile form.

---

## Troubleshooting Common Profile Issues

### Profile Data Not Loading

**Symptoms**: Profile page shows loading spinner indefinitely or displays empty fields

**Possible Causes and Solutions**:

1. **Authentication Issue**:
   - Try logging out and back in
   - Check browser console for auth-related errors
   - Clear browser cookies and cache

2. **Network Connectivity**:
   - Verify your internet connection
   - Check if other features of the application are working

3. **Server Issues**:
   - If the problem persists across devices, our servers may be experiencing issues
   - Check our status page or contact support

### Profile Updates Not Saving

**Symptoms**: Changes to profile fields don't persist after navigation or page refresh

**Possible Causes and Solutions**:

1. **Save Failure**:
   - Look for an "Update failed" message in the UI
   - Click "Save Changes" again
   - Check the browser console for API errors

2. **Validation Errors**:
   - Ensure all required fields are filled correctly
   - Check for specific validation error messages under form fields

3. **Session Expiration**:
   - Your authentication session may have expired
   - Try refreshing the page or logging in again

### Profile Picture Upload Issues

**Symptoms**: Unable to upload or update profile picture

**Possible Causes and Solutions**:

1. **File Format/Size**:
   - Ensure the image is in a supported format (JPEG, PNG, WebP or GIF)
   - Check that the file size is under 5MB
   - Try resizing or converting the image

2. **Browser Permissions**:
   - The browser might be blocking file access
   - Check and enable file permissions for the site

3. **Upload limit**:
   - Picture uploads are limited to 5 per minute
   - Contact support if you consistently cannot upload images

### Account Deletion Problems

**Symptoms**: "Delete Account" action fails or hangs

**Possible Causes and Solutions**:

1. **Confirmation Error**:
   - Ensure you've entered your email address exactly as registered
   - Check for spaces or capitalization differences

2. **Ongoing Operations**:
   - Wait for any in-progress operations to complete
   - Try again after a few minutes

3. **Permissions Issue**:
   - You may have special permissions or restrictions
   - Contact support for assistance with account deletion

---

## Security Considerations

### Data Protection

Auto Author implements several measures to protect your profile data:

1. **Input Sanitization**: text fields in a profile update are sanitized before storage
2. **Rate Limiting**: the profile endpoints have rate limits (see [API Profile Endpoints](../api/profile.md))
3. **Input Validation**: the form and the API validate field lengths and types
4. **Secure Communication**: staging and production serve the app over HTTPS

### Identity and Profile Data

better-auth stores your email, password hash, sessions and two-factor secret. The application backend stores your profile, preferences and content, and links them to your account by its better-auth id. The backend authenticates each request from your session cookie.

### Account Recovery Options

If you lose access to your account:

1. **Password Reset**: Use the "Forgot password?" link on the sign-in page
2. **Lost two-factor device**: Use a backup code, or email support@autoauthor.app

### Best Practices for Users

To maintain the security of your profile:

1. **Use Strong Passwords**: Create unique passwords with a mix of characters
2. **Enable Two-Factor Authentication**: Add an extra layer of security with 2FA
3. **Review Sessions**: Check Active Sessions in Settings → Security and sign out devices you do not recognize
4. **Log Out on Shared Devices**: Always sign out when using public computers

---

*For additional help, please contact our support team at support@autoauthor.app*
