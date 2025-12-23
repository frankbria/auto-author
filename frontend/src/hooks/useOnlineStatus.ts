/**
 * useOnlineStatus Hook
 *
 * Monitors network connectivity and provides real-time online/offline status
 */

import { useState, useEffect, useRef } from 'react';

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
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Only run in browser environment
    if (typeof window === 'undefined') {
      return;
    }

    const handleOnline = () => {
      // Use functional form to read latest state and avoid stale closure
      setIsOnline(prevIsOnline => {
        // If we were offline, mark that we've recovered
        if (!prevIsOnline) {
          setWasOffline(true);
          // Clear any existing timeout before starting new one
          if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
          }
          // Reset the wasOffline flag after a delay
          timeoutRef.current = setTimeout(() => {
            setWasOffline(false);
            timeoutRef.current = null; // Reset ref when timer completes
          }, 5000);
        }
        return true;
      });
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
      // Clear timeout on unmount to prevent memory leaks
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []); // Removed isOnline from dependencies - no longer needed with functional setState

  return { isOnline, wasOffline };
}
