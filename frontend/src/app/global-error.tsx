'use client';

// Root-level error boundary (#334). Catches render errors that escape the root
// layout — the App Router only invokes this when error.tsx itself can't (e.g. a
// layout-level failure), so it must render its own <html>/<body>. Errors caught
// by a boundary never reach window.onerror, so we capture explicitly.
import { useEffect } from 'react';
import * as Sentry from '@sentry/nextjs';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
    console.error('Global application error:', error);
  }, [error]);

  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-950 text-gray-100 flex items-center justify-center p-4">
        <div className="w-full max-w-md text-center space-y-4">
          <h1 className="text-xl font-semibold text-red-400">Something went wrong!</h1>
          <p className="text-gray-400">
            An unexpected error occurred. Please try again or contact support if the
            problem persists.
          </p>
          <button
            onClick={reset}
            className="rounded-md bg-indigo-600 px-4 py-2 hover:bg-indigo-700"
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
