'use client';

import { useAuth } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

/**
 * A component wrapper that ensures the user is authenticated
 * before rendering child components. Redirects to sign-in if not authenticated.
 *
 * Can be bypassed with NEXT_PUBLIC_BYPASS_AUTH=true for E2E testing.
 */
export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isLoaded, userId, isSignedIn } = useAuth();
  const router = useRouter();

  // Check if auth bypass is enabled for E2E testing
  const bypassAuth = process.env.NEXT_PUBLIC_BYPASS_AUTH === 'true';

  useEffect(() => {
    // Skip auth checks if bypass is enabled
    if (bypassAuth) return;

    // Wait for auth to load before making decisions
    if (!isLoaded) return;

    // If not signed in, redirect to sign-in page
    if (!isSignedIn) {
      router.push('/sign-in');
    }
  }, [bypassAuth, isLoaded, isSignedIn, router, userId]);

  // If auth bypass is enabled, render children immediately
  if (bypassAuth) {
    return <>{children}</>;
  }

  // Show nothing while loading or if not authenticated
  if (!isLoaded || !isSignedIn) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  // User is authenticated, render children
  return <>{children}</>;
}
