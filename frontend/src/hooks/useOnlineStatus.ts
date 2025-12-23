/**
 * useOnlineStatus Hook
 *
 * Monitors network connectivity and provides real-time online/offline status
 */

import { useState, useEffect } from 'react';

export interface OnlineStatus {
  isOnline: boolean;
  wasOffline: boolean;
}

/**
 * Hook to detect browser online/offline status
 *
 * @returns Object containing isOnline status and wasOffline flag
 */
export function useOnlineStatus(): OnlineStatus {
  const [isOnline, setIsOnline] = useState(
    typeof window !== 'undefined' ? window.navigator.onLine : true
  );
  const [wasOffline, setWasOffline] = useState(false);

  useEffect(() => {
    // Only run in browser environment
    if (typeof window === 'undefined') {
      return;
    }

    const handleOnline = () => {
      setIsOnline(true);
      // If we were offline, mark that we've recovered
      if (!isOnline) {
        setWasOffline(true);
        // Reset the wasOffline flag after a delay
        setTimeout(() => setWasOffline(false), 5000);
      }
    };

    const handleOffline = () => {
      setIsOnline(false);
    };

    // Add event listeners
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Cleanup
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [isOnline]);

  return { isOnline, wasOffline };
}
