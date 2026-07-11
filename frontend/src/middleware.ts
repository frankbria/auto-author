// frontend/src/middleware.ts

import { NextRequest, NextResponse } from 'next/server';
import { buildCsp } from '@/lib/csp';

// Middleware for route protection using better-auth session cookies
// This will:
// 1. Verify authentication for protected routes by checking session cookie
// 2. Redirect unauthenticated users to sign-in page
// 3. Keep middleware Edge Runtime compatible (no better-auth imports)
// 4. Set a per-request nonce-based CSP (#190) — see lib/csp.ts
//
// For E2E testing: Set BYPASS_AUTH=true (server-only) to skip authentication

// Forward the nonce'd CSP on both the request (Next.js reads it to stamp its
// inline scripts; layout reads x-nonce for next-themes) and the response.
function withCsp(request: NextRequest): NextResponse {
  const nonce = btoa(crypto.randomUUID());
  const csp = buildCsp(nonce, { isDev: process.env.NODE_ENV === 'development' });

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-nonce', nonce); // set(), not append — clobbers any client-sent value
  requestHeaders.set('Content-Security-Policy', csp);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set('Content-Security-Policy', csp);
  return response;
}

export async function middleware(request: NextRequest) {
  // SECURITY: Use server-side only env var (NOT NEXT_PUBLIC_)
  // This prevents exposing test mode to client-side code
  const bypassAuth = process.env.BYPASS_AUTH === 'true';

  // Production safety check - prevent accidental bypass in production.
  // The ONLY exemption is the purpose-built E2E_ALLOW_BYPASS=1 flag, set
  // explicitly by the Playwright webServer config and never by real deploys.
  // Deliberately NOT keyed on the generic CI env var (#192): CI=true is set
  // by most CI/PaaS/container runtimes, so it would silently disable auth in
  // any production artifact that happens to run with it.
  const e2eAllowBypass = process.env.E2E_ALLOW_BYPASS === '1';
  if (bypassAuth && process.env.NODE_ENV === 'production' && !e2eAllowBypass) {
    console.error('FATAL: BYPASS_AUTH cannot be enabled in production environment');
    throw new Error(
      'FATAL SECURITY ERROR: BYPASS_AUTH is enabled in production. ' +
      'This completely disables authentication. Set BYPASS_AUTH=false immediately.'
    );
  }

  // Allow bypass for E2E tests (development/test environments only)
  if (bypassAuth) {
    console.warn('⚠️  BYPASS_AUTH enabled - authentication is disabled for testing');
    return withCsp(request);
  }

  const { pathname } = request.nextUrl;

  // Define protected routes
  const isProtectedRoute =
    pathname.startsWith('/dashboard') || pathname.startsWith('/profile');

  // Skip session check for public routes
  if (!isProtectedRoute) {
    return withCsp(request);
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
  return withCsp(request);
}

export const config = {
  matcher: [
    // Match all routes except static files and API routes
    // This allows public routes while protecting dashboard routes
    '/((?!_next/static|_next/image|favicon.ico|api/).*)',
  ]
};
