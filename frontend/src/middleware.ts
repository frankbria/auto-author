// frontend/src/middleware.ts

import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth';

// Middleware for route protection using better-auth
// This will:
// 1. Verify authentication for protected routes
// 2. Redirect unauthenticated users to sign-in page
// 3. Provide session context to your application
//
// For E2E testing: Set NEXT_PUBLIC_BYPASS_AUTH=true to skip authentication
export async function middleware(request: NextRequest) {
  // Allow bypassing auth for E2E tests
  // NOTE: Must use NEXT_PUBLIC_ prefix to be available in middleware
  if (process.env.NEXT_PUBLIC_BYPASS_AUTH === 'true' || process.env.NEXT_PUBLIC_ENVIRONMENT === 'test') {
    return NextResponse.next();
  }

  const { pathname } = request.nextUrl;

  // Define protected routes
  const isProtectedRoute = pathname.startsWith('/dashboard');

  // Skip session check for public routes
  if (!isProtectedRoute) {
    return NextResponse.next();
  }

  // Get session from better-auth
  try {
    const session = await auth.api.getSession({
      headers: request.headers
    });

    // Redirect to sign-in if accessing protected route without session
    if (!session) {
      const signInUrl = new URL('/auth/sign-in', request.url);
      signInUrl.searchParams.set('redirect', pathname);
      return NextResponse.redirect(signInUrl);
    }

    // Allow request to proceed
    return NextResponse.next();
  } catch (error) {
    // If session check fails, redirect to sign-in
    console.error('Session validation error:', error);
    const signInUrl = new URL('/auth/sign-in', request.url);
    signInUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(signInUrl);
  }
}

export const config = {
  matcher: [
    // Match all routes except static files and API routes
    // This allows public routes while protecting dashboard routes
    '/((?!_next/static|_next/image|favicon.ico|api/).*)',
  ]
};