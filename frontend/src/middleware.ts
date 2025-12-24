// frontend/src/middleware.ts

import { NextRequest, NextResponse } from 'next/server';

// Middleware for route protection using better-auth session cookies
// This will:
// 1. Verify authentication for protected routes by checking session cookie
// 2. Redirect unauthenticated users to sign-in page
// 3. Keep middleware Edge Runtime compatible (no better-auth imports)
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

  // Check for better-auth session cookie
  // In production (HTTPS), better-auth sets '__Secure-better-auth.session_token'
  // In development (HTTP), it sets 'better-auth.session_token'
  const sessionToken = request.cookies.get('__Secure-better-auth.session_token')
    || request.cookies.get('better-auth.session_token');

  // Redirect to sign-in if accessing protected route without session
  if (!sessionToken) {
    const signInUrl = new URL('/auth/sign-in', request.url);
    signInUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(signInUrl);
  }

  // Allow request to proceed - actual session validation happens in API routes
  return NextResponse.next();
}

export const config = {
  matcher: [
    // Match all routes except static files and API routes
    // This allows public routes while protecting dashboard routes
    '/((?!_next/static|_next/image|favicon.ico|api/).*)',
  ]
};