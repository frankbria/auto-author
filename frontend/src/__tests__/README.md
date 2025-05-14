# Auto Author Frontend Testing

This directory contains tests for the Auto Author frontend application. The tests use Jest and React Testing Library to validate component behavior and application functionality.

## Authentication Testing

We have implemented several test suites to validate the Clerk authentication integration:

1. **SignUp.test.tsx** - Tests the Clerk SignUp component integration:
   - Verifies that the SignUp component renders correctly
   - Tests that routing props are correctly passed to Clerk
   - Validates loading and error states

2. **AuthPersistence.test.tsx** - Tests authentication state persistence:
   - Verifies that authenticated sessions are maintained across renders
   - Tests behavior when authentication state changes
   - Validates token persistence and refresh behavior

3. **ProtectedRoute.test.tsx** - Tests the protected route component:
   - Validates redirect behavior for unauthenticated users
   - Tests loading states during authentication
   - Verifies protected content only displays for authenticated users

4. **useAuthFetch.test.tsx** - Tests the authentication fetch hook:
   - Verifies that auth tokens are correctly included in API requests
   - Tests token persistence across multiple requests
   - Validates token refresh behavior when tokens expire

## Running Tests

Run all tests:
```bash
npm test
```

Run with coverage:
```bash
npm test -- --coverage
```

Run specific test file:
```bash
npm test -- SignUp.test.tsx
```

## Testing Best Practices

- **Mock External Dependencies**: Use Jest mocks for Next.js hooks like `useRouter` and Clerk's `useAuth`
- **Test User Flows**: Focus on testing complete user flows rather than implementation details
- **Test Loading States**: Always test loading states to ensure good UX
- **Test Error Handling**: Verify that errors are handled gracefully
- **Test Auth Transitions**: Validate behavior when auth state changes (sign in, sign out, etc.)
