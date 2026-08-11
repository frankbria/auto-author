'use client';

import { reloadPage } from '@/lib/navigation';

/**
 * RefreshButton - Client Component for page refresh
 * Extracted from ErrorBoundary to avoid "Event handlers in Server Component" error
 */
export function RefreshButton() {
  return (
    <button
      onClick={() => reloadPage()}
      className="bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded transition-colors"
      aria-label="Refresh page"
    >
      Refresh Page
    </button>
  );
}
