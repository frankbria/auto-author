# Frontend Profile Components Documentation

This document provides technical documentation for the frontend components related to profile management in Auto Author.

## Overview

Auto Author's profile management implementation consists of React components and hooks that interact with the backend API to manage user profile data. The frontend maintains a clean separation of concerns with:

1. UI components for displaying and editing profile information
2. Custom hooks for API interaction
3. Form validation schemas
4. Authentication state management via Clerk

## Key Components

### 1. User Profile Page Component

Located at `frontend/src/app/profile/page.tsx`, this is the main profile management page component.

**Key Features:**
- Profile data fetching and state management
- Form-based profile editing
- Avatar/profile picture management
- Theme preference switching
- Notification preferences
- Form validation with Zod schema

**Usage:**
The profile page is accessible via the `/profile` route and requires authentication.

### 2. Profile API Hook

Located at `frontend/src/hooks/useProfileApi.ts`, this custom hook encapsulates all API interactions related to profile management.

**Available Methods:**
- `getUserProfile()` - Fetches current user profile data
- `updateUserProfile(data)` - Updates profile information
- `uploadProfilePicture(file)` - Handles avatar image uploads
- `deleteUserAccount()` - Manages account deletion

**Example Usage:**
```typescript
const { getUserProfile, updateUserProfile } = useProfileApi();

// Fetch profile data
const profileData = await getUserProfile();

// Update profile
await updateUserProfile({ 
  first_name: "Jane", 
  last_name: "Doe",
  preferences: { theme: "dark" }
});
```

## Form Validation

Profile data validation uses Zod schema validation:

```typescript
const profileFormSchema = z.object({
  firstName: z.string().min(1, "First name is required"),
  lastName: z.string().min(1, "Last name is required"),
  bio: z.string().optional(),
  avatarUrl: z.string().optional(),
  theme: z.enum(["light", "dark", "system"]),
  emailNotifications: z.boolean(),
  marketingEmails: z.boolean()
});
```

## Data Flow

1. User loads profile page → `useUser()` hook from Clerk provides auth data
2. Component calls `getUserProfile()` from `useProfileApi` hook
3. Profile data renders in form fields
4. User makes changes → form validation occurs
5. On submit → `updateUserProfile()` sends data to API
6. Toast notifications provide feedback on success/failure

## Related Documentation

- [Profile Management Guide](profile-management-guide.md) - User-facing profile documentation
- [API Profile Endpoints](api-profile-endpoints.md) - Backend API documentation
- [Profile Testing Guide](profile-testing-guide.md) - Testing and CI/CD for profile features
- [Authentication User Guide](user-guide-auth.md) - General authentication documentation
