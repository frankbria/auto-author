'use client';

import { useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { HugeiconsIcon } from '@hugeicons/react';
import { Alert02Icon, RefreshIcon } from '@hugeicons/core-free-icons';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error('Application error:', error);
  }, [error]);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex items-center justify-center p-4">
      <Card className="w-full max-w-md bg-gray-900 border-gray-800">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <HugeiconsIcon icon={Alert02Icon} size={64} className="text-red-400" />
          </div>
          <CardTitle className="text-xl font-semibold text-red-400">
            Something went wrong!
          </CardTitle>
          <CardDescription className="text-gray-400">
            An unexpected error occurred. Please try again or contact support if the problem persists.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {process.env.NODE_ENV === 'development' && (
            <div className="bg-gray-800 p-3 rounded-md">
              <h3 className="text-sm font-medium text-gray-300 mb-2">Error Details:</h3>
              <p className="text-xs text-gray-400 font-mono break-all">
                {error.message}
              </p>
              {error.digest && (
                <p className="text-xs text-gray-500 mt-1">
                  Digest: {error.digest}
                </p>
              )}
            </div>
          )}
          <div className="flex gap-2">
            <Button
              onClick={reset}
              className="flex-1 bg-indigo-600 hover:bg-indigo-700"
            >
              <HugeiconsIcon icon={RefreshIcon} size={16} className="mr-2" />
              Try again
            </Button>
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => window.location.href = '/dashboard'}
            >
              Go to Dashboard
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}