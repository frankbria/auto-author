// frontend/src/middleware.ts

import { clerkMiddleware } from '@clerk/nextjs/server';
import { NextResponse } from 'next/server';

// Export the Clerk middleware for route protection
// This will:
// 1. Verify authentication for protected routes
// 2. Redirect unauthenticated users to sign-in page
// 3. Provide auth context to your application
//
// For E2E testing: Set NEXT_PUBLIC_BYPASS_AUTH=true to skip authentication
export default clerkMiddleware(async (auth, req) => {
  // Allow bypassing auth for E2E tests
  // NOTE: Must use NEXT_PUBLIC_ prefix to be available in middleware
  if (process.env.NEXT_PUBLIC_BYPASS_AUTH === 'true' || process.env.NEXT_PUBLIC_ENVIRONMENT === 'test') {
    return NextResponse.next();
  }

  // Enforce authentication for protected routes
  // This will redirect unauthenticated users to the sign-in page
  await auth().protect();

  return NextResponse.next();
});

export const config = {
  matcher: [
    // Dashboard routes (always protected)
    '/dashboard/:path*',
    
    // API routes
    '/(api|trpc)(.*)',
    
    // Exclude public routes and static assets
    // This pattern matches all routes EXCEPT:
    // - The root path (/)
    // - Static files (_next/*, *.js, *.css, etc.)
    // - Sign-in related paths (sign-in, sign-in/*)
    // - Sign-up related paths (sign-up, sign-up/*)
    '/((?!api|_next|.*\\.(?:jpg|jpeg|gif|svg|png|js|css|woff|woff2|ttf|ico))(?!sign-in)(?!sign-up).*)'
  ]
};