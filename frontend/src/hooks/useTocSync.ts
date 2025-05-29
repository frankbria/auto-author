import { useEffect, useRef, useCallback } from 'react';
import bookClient from '@/lib/api/bookClient';

interface UseTocSyncOptions {
  bookId: string;
  onTocChanged: () => void;
  pollInterval?: number;
}

/**
 * Hook to detect TOC changes and trigger synchronization
 * Uses localStorage events and optional polling to detect when TOC has been modified
 */
export function useTocSync({ bookId, onTocChanged, pollInterval = 0 }: UseTocSyncOptions) {
  const lastTocHashRef = useRef<string | null>(null);
  const pollTimeoutRef = useRef<NodeJS.Timeout | null>(null);  // Function to generate a simple hash of TOC structure for change detection
  const generateTocHash = useCallback(async (): Promise<string | null> => {
    try {
      // Use bookClient instead of direct fetch to avoid URL duplication
      const tocResponse = await bookClient.getToc(bookId);
      if (!tocResponse.toc) return null;
      
      // Create a simple hash based on chapter structure
      const hashSource = JSON.stringify({
        chapters: tocResponse.toc.chapters.map((ch) => ({
          id: ch.id,
          title: ch.title,
          order: ch.order,
          subchapters: ch.subchapters?.map((sub) => ({
            id: sub.id,
            title: sub.title,
            order: sub.order
          })) || []
        }))
      });
      
      // Simple hash function
      let hash = 0;
      for (let i = 0; i < hashSource.length; i++) {
        const char = hashSource.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32bit integer
      }
      return hash.toString();
    } catch (error) {
      console.error('Failed to generate TOC hash:', error);
      return null;
    }
  }, [bookId]);

  // Function to check for TOC changes
  const checkForTocChanges = useCallback(async () => {
    const currentHash = await generateTocHash();
    
    if (currentHash && lastTocHashRef.current && currentHash !== lastTocHashRef.current) {
      console.log('TOC change detected, triggering sync');
      onTocChanged();
    }
    
    lastTocHashRef.current = currentHash;
  }, [generateTocHash, onTocChanged]);

  // Listen for custom TOC update events
  useEffect(() => {
    const handleTocUpdate = (event: CustomEvent) => {
      if (event.detail.bookId === bookId) {
        console.log('TOC update event received, triggering sync');
        onTocChanged();
      }
    };

    window.addEventListener('tocUpdated', handleTocUpdate as EventListener);
    
    return () => {
      window.removeEventListener('tocUpdated', handleTocUpdate as EventListener);
    };
  }, [bookId, onTocChanged]);

  // Listen for localStorage changes (for cross-tab sync)
  useEffect(() => {
    const handleStorageChange = (event: StorageEvent) => {
      if (event.key === `toc-updated-${bookId}` && event.newValue) {
        console.log('TOC update detected via localStorage, triggering sync');
        onTocChanged();
        // Clear the flag after handling
        localStorage.removeItem(`toc-updated-${bookId}`);
      }
    };

    window.addEventListener('storage', handleStorageChange);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, [bookId, onTocChanged]);
  // Optional polling for changes (fallback mechanism)
  useEffect(() => {
    if (pollInterval > 0) {
      const startPolling = async () => {
        // Initialize the hash
        lastTocHashRef.current = await generateTocHash();
        
        const poll = async () => {
          await checkForTocChanges();
          pollTimeoutRef.current = setTimeout(poll, pollInterval);
        };
        
        pollTimeoutRef.current = setTimeout(poll, pollInterval);
      };

      startPolling();

      return () => {
        if (pollTimeoutRef.current) {
          clearTimeout(pollTimeoutRef.current);
        }
      };
    }
  }, [bookId, pollInterval, onTocChanged, checkForTocChanges, generateTocHash]);

  // Cleanup
  useEffect(() => {
    return () => {
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
      }
    };
  }, []);
}

/**
 * Utility function to trigger a TOC update event
 * Call this after successfully saving TOC changes
 */
export function triggerTocUpdateEvent(bookId: string) {
  // Dispatch custom event
  const event = new CustomEvent('tocUpdated', {
    detail: { bookId, timestamp: Date.now() }
  });
  window.dispatchEvent(event);
  
  // Set localStorage flag for cross-tab communication
  localStorage.setItem(`toc-updated-${bookId}`, Date.now().toString());
  
  console.log('TOC update event triggered for book:', bookId);
}
