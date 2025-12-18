// frontend/src/middleware.ts

import { NextRequest, NextResponse } from 'next/server';
import { getAuth } from '@/lib/auth';

// Middleware for route protection using better-auth
// This will:
// 1. Verify authentication for protected routes
// 2. Redirect unauthenticated users to sign-in page
// 3. Provide session context to your application
//
// For E2E testing: Set BYPASS_AUTH=true (server-only) to skip authentication
export async function middleware(request: NextRequest) {
  // SECURITY: Use server-side only env var (NOT NEXT_PUBLIC_)
  // This prevents exposing test mode to client-side code
  const bypassAuth = process.env.BYPASS_AUTH === 'true';

  // Production safety check - prevent accidental bypass in production
  if (bypassAuth && process.env.NODE_ENV === 'production') {
    console.error('FATAL: BYPASS_AUTH cannot be enabled in production environment');
    throw new Error(
      'FATAL SECURITY ERROR: BYPASS_AUTH is enabled in production. ' +
      'This completely disables authentication. Set BYPASS_AUTH=false immediately.'
    );
  }

  // Allow bypass for E2E tests (development/test environments only)
  if (bypassAuth) {
    console.warn('⚠️  BYPASS_AUTH enabled - authentication is disabled for testing');
    return NextResponse.next();
  }

  const { pathname } = request.nextUrl;

  // Define protected routes
  const isProtectedRoute = pathname.startsWith('/dashboard');

  // Skip session check for public routes
  if (!isProtectedRoute) {
    return NextResponse.next();
  }

  // Get session from better-auth with connected MongoDB client
  try {
    const auth = await getAuth();
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