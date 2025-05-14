// frontend/src/middleware.ts

import { clerkMiddleware } from '@clerk/nextjs/server';

// Export the Clerk middleware for route protection
// This will:
// 1. Verify authentication for protected routes
// 2. Redirect unauthenticated users to sign-in page
// 3. Provide auth context to your application
export default clerkMiddleware();

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