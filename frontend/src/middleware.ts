// frontend/src/middleware.ts

import { clerkMiddleware } from '@clerk/nextjs/server';
import { NextResponse } from 'next/server';

// Export the Clerk middleware for route protection
// This will:
// 1. Verify authentication for protected routes
// 2. Redirect unauthenticated users to sign-in page
// 3. Provide auth context to your application
export default clerkMiddleware(async (auth, req) => {
  // Enforce authentication for protected routes
  // This will redirect unauthenticated users to the sign-in page
  await auth.protect();

  return NextResponse.next();
});

export const config = {
  matcher: [
    // Only protect dashboard routes - leave root path (/) public for landing page
    '/dashboard/:path*',
  ]
};