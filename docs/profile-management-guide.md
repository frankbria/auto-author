# Profile Management Documentation

This guide provides comprehensive information about the profile management features in Auto Author, including user options, editing procedures, API endpoints, troubleshooting, and security considerations.

## Table of Contents

1. [Profile Management Features](#profile-management-features)
2. [User Guide for Profile Editing](#user-guide-for-profile-editing)
3. [API Endpoints for Profile Operations](#api-endpoints-for-profile-operations)
4. [Troubleshooting Common Profile Issues](#troubleshooting-common-profile-issues)
5. [Security Considerations](#security-considerations)

---

## Related Documentation

- [API Profile Endpoints](api-profile-endpoints.md) - Detailed API documentation for profile operations
- [Frontend Profile Components](frontend-profile-components.md) - Technical docs for profile UI components
- [Profile Testing Guide](profile-testing-guide.md) - Testing and CI/CD for profile features
- [Authentication User Guide](user-guide-auth.md) - General authentication documentation
- [Clerk Integration Guide](clerk-integration-guide.md) - How Clerk authentication is integrated
- [Auth Troubleshooting](auth-troubleshooting.md) - Solutions for common authentication issues

---

## Profile Management Features

Auto Author's profile management system integrates with Clerk for authentication while maintaining application-specific user data in our own database. This hybrid approach offers several advantages:

### Core Features

- **Basic Information Management**: Edit first name, last name, and bio
- **Profile Picture Management**: Upload and update profile pictures
- **User Preferences**: Customize application appearance and notification settings
- **Account Management**: Options for account deletion
- **Auto-save Functionality**: Changes are saved automatically as you type

### User Preferences Options

Auto Author supports the following user preferences:

| Preference | Description | Default Value |
|------------|-------------|---------------|
| Theme | UI color scheme (light/dark/system) | Dark |
| Email Notifications | Receive important updates | Enabled |
| Marketing Emails | Receive promotional content | Disabled |

### Data Synchronization

Profile changes are synchronized in two places:
1. **Clerk**: For authentication-related data (name, email, password)
2. **Auto Author Backend**: For application-specific data (preferences, bio)

This dual-storage approach ensures a seamless user experience while maintaining data integrity across systems.

---

## User Guide for Profile Editing

### Accessing Your Profile

1. **Navigate to Profile**: Click your avatar in the top-right corner of any page, then select "Profile" from the dropdown menu
2. **Direct Access**: Go directly to `/profile` in your browser

### Editing Basic Information

1. **Name Fields**: Update your first and last name in the corresponding fields
2. **Bio**: Share information about yourself in the bio text area
3. **Email**: Your email is managed through Clerk and can be changed via the "Change" button

All text fields feature automatic saving - changes are applied as you type after a short delay.

### Managing Your Profile Picture

1. **View Current Picture**: Your profile image appears at the top of the profile page
2. **Change Picture**:
   - Click the edit icon (pencil) on the profile picture
   - Select an image from your device
   - The image will be automatically uploaded and displayed

### Setting Preferences

Your preferences are found in the "Preferences" section:

1. **Theme Selection**:
   - **Light**: Bright theme for daytime use
   - **Dark**: Dark theme to reduce eye strain (default)
   - **System**: Follows your device settings

2. **Notification Preferences**:
   - Toggle "Email Notifications" to receive account updates
   - Toggle "Marketing Emails" to receive promotional content

### Account Management

In the "Account Settings" section, you can:

1. **Change Password**: Click "Change Password" to update your credentials through Clerk
2. **Delete Account**:
   - Click "Delete Account"
   - Confirm by typing your email address in the prompt
   - Click "Delete Account" in the confirmation dialog

> ⚠️ **Warning**: Account deletion is permanent and will remove all your data from Auto Author.

---

## API Endpoints for Profile Operations

Auto Author provides several API endpoints for profile management. All endpoints require authentication via Clerk JWT tokens.

### Base URL

```
https://api.auto-author.com/v1
```

For local development:

```
http://localhost:8000
```

### Current User Profile

**Endpoint**: `GET /users/me`

**Description**: Retrieves the current authenticated user's profile information

**Authentication**: Required

**Response Format**:
```json
{
  "id": "string",
  "clerk_id": "string",
  "email": "user@example.com",
  "first_name": "string",
  "last_name": "string",
  "display_name": "string",
  "avatar_url": "string",
  "bio": "string",
  "role": "user",
  "created_at": "2025-05-01T12:00:00Z",
  "updated_at": "2025-05-17T12:00:00Z",
  "books": [],
  "preferences": {
    "theme": "dark",
    "email_notifications": true,
    "marketing_emails": false
  }
}
```

**Status Codes**:
- `200 OK`: Profile retrieved successfully
- `401 Unauthorized`: Invalid or missing authentication token
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
- `401 Unauthorized`: Invalid or missing authentication token
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server-side error

### Delete Account

**Endpoint**: `DELETE /users/me`

**Description**: Permanently deletes the current user's account and all associated data

**Authentication**: Required

**Rate Limiting**: 3 requests per 5 minutes

**Response Format**:
```json
{
  "message": "Account successfully deleted"
}
```

**Status Codes**:
- `200 OK`: Account deleted successfully
- `401 Unauthorized`: Invalid or missing authentication token
- `404 Not Found`: User not found or already deleted
- `429 Too Many Requests`: Rate limit exceeded

### Clerk User Data

**Endpoint**: `GET /users/clerk/{clerk_id}`

**Description**: Fetches user data directly from Clerk (limited access)

**Authentication**: Required (admin or self only)

**Response Format**:
```json
{
  "id": "string",
  "first_name": "string",
  "last_name": "string",
  "email_addresses": [
    {
      "email": "user@example.com",
      "verified": true
    }
  ]
}
```

**Status Codes**:
- `200 OK`: Data retrieved successfully
- `401 Unauthorized`: Invalid or missing authentication token
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: User not found in Clerk

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

1. **Auto-save Failure**:
   - Look for error messages in the UI
   - Try clicking the "Save Changes" button explicitly
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
   - Ensure the image is in a supported format (JPEG, PNG, GIF)
   - Check that the file size is under 5MB
   - Try resizing or converting the image

2. **Browser Permissions**:
   - The browser might be blocking file access
   - Check and enable file permissions for the site

3. **Storage Issues**:
   - Clerk storage limits may have been reached
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

1. **Input Sanitization**: All profile data is sanitized before storage to prevent XSS attacks
2. **Rate Limiting**: API endpoints have rate limits to prevent brute force attacks
3. **Input Validation**: Strict validation rules ensure data integrity
4. **Audit Logging**: All profile changes are logged for security monitoring
5. **Secure Communication**: All API calls use HTTPS encryption

### Two-System Security Model

Our profile system uses a two-system security model:

1. **Clerk Authentication System**:
   - Manages critical identity data and credentials
   - Handles password security and MFA
   - Provides JWT tokens for API authentication

2. **Application Backend**:
   - Stores application-specific user data
   - Manages preferences and content
   - Links content to authenticated users via Clerk IDs

This separation creates multiple security layers, reducing vulnerability to attacks.

### Account Recovery Options

If you lose access to your account:

1. **Password Reset**: Use the "Forgot Password" option on the login screen
2. **Email Recovery**: Verify your identity via email verification
3. **Support Assistance**: Contact our support team for account recovery help

### Best Practices for Users

To maintain the security of your profile:

1. **Use Strong Passwords**: Create unique passwords with a mix of characters
2. **Enable Two-Factor Authentication**: Add an extra layer of security with 2FA
3. **Monitor Activity**: Regularly check for unusual activity in your account
4. **Update Contact Information**: Keep your email and recovery options current
5. **Log Out on Shared Devices**: Always sign out when using public computers

---

*For additional help, please contact our support team at support@auto-author.com*
