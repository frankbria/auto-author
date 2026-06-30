'use client';

import { useSession } from '@/lib/auth-client';
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
  const { data: session, isPending } = useSession();
  const router = useRouter();

  // Check if auth bypass is enabled for E2E testing
  const bypassAuth = process.env.NEXT_PUBLIC_BYPASS_AUTH === 'true';

  useEffect(() => {
    // Skip auth checks if bypass is enabled
    if (bypassAuth) return;

    // Wait for session to load before making decisions
    if (isPending) return;

    // If not signed in, redirect to sign-in page
    if (!session) {
      router.push('/auth/sign-in');
    }
  }, [bypassAuth, isPending, session, router]);

  // If auth bypass is enabled, render children immediately
  if (bypassAuth) {
    return <>{children}</>;
  }

  // While loading/redirecting, still render the <main id="main-content"> landmark
  // so the global skip link always has a target (and the page has a main landmark).
  if (isPending || !session) {
    return (
      <main
        id="main-content"
        tabIndex={-1}
        className="flex items-center justify-center min-h-screen"
      >
        <div role="status" aria-live="polite">
          <span className="sr-only">Loading…</span>
          <div
            className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"
            aria-hidden="true"
          ></div>
        </div>
      </main>
    );
  }

  // User is authenticated, render children
  return <>{children}</>;
}
