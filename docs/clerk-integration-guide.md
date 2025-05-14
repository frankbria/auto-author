# Clerk Integration Guide for Auto Author

This document provides detailed information about how Auto Author integrates with Clerk for authentication and user management.

## Overview

Auto Author uses [Clerk](https://clerk.dev/) for authentication, providing:

- Secure user registration and login
- Social login options (Google, GitHub, etc.)
- Multi-factor authentication
- Email verification
- Session management across devices
- Password reset functionality

## Architecture

![Authentication Flow](https://via.placeholder.com/800x400?text=Auth+Flow+Diagram)

### How It Works

1. **Frontend Authentication**: Users authenticate via Clerk components embedded in our Next.js frontend
2. **Backend Verification**: API requests include JWT tokens verified by our FastAPI backend
3. **User Mapping**: Each Clerk user has a corresponding entry in our application database
4. **Webhooks**: User events from Clerk (creation, updates, deletion) sync with our database

## Integration Components

### Frontend Integration

1. **Clerk Provider**: Wraps the application to provide authentication context
   ```tsx
   // In _app.tsx or layout.tsx
   import { ClerkProvider } from '@clerk/nextjs';
   
   export default function Layout({ children }: { children: React.ReactNode }) {
     return (
       <ClerkProvider>
         {children}
       </ClerkProvider>
     );
   }
   ```

2. **Authentication Components**: Pre-built UI for authentication flows
   ```tsx
   // In sign-up/[[...rest]]/page.tsx
   import { SignUp } from '@clerk/nextjs';
   
   export default function SignUpPage() {
     return (
       <SignUp 
         path="/sign-up"
         signInUrl="/sign-in"
         redirectUrl="/dashboard"
         appearance={{
           // Custom styling
         }}
       />
     );
   }
   ```

3. **Protected Routes**: Using middleware to protect routes that require authentication
   ```tsx
   // In middleware.ts
   import { clerkMiddleware } from '@clerk/nextjs/server';
   
   export default clerkMiddleware();
   
   export const config = {
     matcher: [
       '/dashboard/:path*',
       '/(api|trpc)(.*)',
       '/((?!api|_next|.*\\.(?:jpg|jpeg|gif|svg|png|js|css))(?!sign-in)(?!sign-up).*)'
     ]
   };
   ```

4. **Client-Side Auth Hooks**: For accessing auth state in React components
   ```tsx
   import { useAuth, useUser } from '@clerk/nextjs';
   
   function MyComponent() {
     const { isSignedIn, userId } = useAuth();
     const { user } = useUser();
     
     return isSignedIn ? <p>Hello {user?.firstName}!</p> : <p>Not signed in</p>;
   }
   ```

### Backend Integration

1. **JWT Verification**: Verifying tokens on the backend
   ```python
   async def verify_jwt_token(token: str) -> Dict[str, Any]:
       """Verify a JWT token from Clerk."""
       try:
           payload = jwt.decode(
               token,
               settings.CLERK_JWT_PUBLIC_KEY,
               algorithms=[settings.CLERK_JWT_ALGORITHM],
               audience="example.com",  # Your domain
               options={"verify_signature": True},
           )
           return payload
       except JWTError as e:
           raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail=f"Invalid authentication credentials: {str(e)}",
           )
   ```

2. **Role-Based Access Control**: Using Clerk metadata for roles
   ```python
   class RoleChecker:
       """Dependency for role-based access control"""
       def __init__(self, allowed_roles: List[str]):
           self.allowed_roles = allowed_roles
   
       async def __call__(self, credentials: HTTPAuthorizationCredentials = Depends(security)):
           # ... verification logic ...
           user = await get_user_by_clerk_id(user_id)
           if user["role"] not in self.allowed_roles:
               raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
   ```

3. **Webhook Handling**: Keeping user data in sync
   ```python
   @router.post("/clerk", status_code=status.HTTP_200_OK)
   async def clerk_webhook(request: Request, verified: bool = Depends(verify_webhook_signature)):
       """Handle webhook events from Clerk"""
       body = await request.body()
       event_data = json.loads(body.decode("utf-8"))
       event_type = event_data.get("type")
       
       # Handle different event types (user.created, user.updated, etc.)
       if event_type == "user.created":
           # Create a new user in our database
           # ...
   ```

## Custom Auth Utilities

For server-side components and API routes, we provide helper functions in `lib/clerk-helpers.ts`:

```tsx
// Get the current auth token for API requests
export async function getAuthToken(): Promise<string | null> {
  try {
    const session = await auth();
    return session.sessionId || null;
  } catch (error) {
    console.error("Error getting auth token:", error);
    return null;
  }
}

// Get the current user from Clerk
export async function getUserInfo() {
  try {
    const user = await currentUser();
    return user;
  } catch (error) {
    console.error("Error getting user info:", error);
    return null;
  }
}
```

For client components that need to make authenticated API requests, we provide the `useAuthFetch` hook:

```tsx
// In hooks/useAuthFetch.ts
export function useAuthFetch(options: UseAuthFetchOptions = {}) {
  const { getToken } = useAuth();
  
  const authFetch = useCallback(async <T = unknown>(path: string, fetchOptions: FetchOptions = {}): Promise<T> => {
    // Add auth token to request headers
    const token = await getToken();
    // Make authenticated fetch request
    // ...
  }, [baseUrl, getToken]);

  return { authFetch, loading, error };
}
```

## Clerk Dashboard Configuration

To configure your Clerk instance:

1. Create a Clerk account and application at https://dashboard.clerk.dev/
2. Configure these settings in the Clerk Dashboard:
   - **Authentication methods**: Email/password, social providers
   - **Custom domains**: Your application domains
   - **JWT settings**: JWKS endpoint and signing algorithm
   - **Webhooks**: Set up webhooks for user events
   - **Email templates**: Customize verification and password reset emails
   - **User metadata**: Configure custom user metadata fields
   - **Session settings**: Control session duration and behavior

## Next Steps

- See the [User Guide](./user-guide.md) for end-user documentation
- See the [Deployment Checklist](./deployment-checklist.md) for production setup
- Visit [Clerk's documentation](https://clerk.dev/docs) for more details about Clerk features
