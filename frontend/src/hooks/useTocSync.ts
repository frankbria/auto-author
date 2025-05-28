import { useEffect, useRef } from 'react';

interface UseTocSyncOptions {
  bookId: string;
  onTocChanged: () => void;
  pollInterval?: number;
}

/**
 * Hook to detect TOC changes and trigger synchronization
 * Uses localStorage events and optional polling to detect when TOC has been modified
 */
export function useTocSync({ bookId, onTocChanged, pollInterval = 2000 }: UseTocSyncOptions) {
  const lastTocHashRef = useRef<string | null>(null);
  const pollTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Function to generate a simple hash of TOC structure for change detection
  const generateTocHash = async (): Promise<string | null> => {
    try {
      // This would normally fetch from your API
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/books/${bookId}/toc`);
      if (!response.ok) return null;
      
      const data = await response.json();
      if (!data.toc) return null;
      
      // Create a simple hash based on chapter structure
      const hashSource = JSON.stringify({
        chapters: data.toc.chapters.map((ch: any) => ({
          id: ch.id,
          title: ch.title,
          order: ch.order,
          subchapters: ch.subchapters?.map((sub: any) => ({
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
  };

  // Function to check for TOC changes
  const checkForTocChanges = async () => {
    const currentHash = await generateTocHash();
    
    if (currentHash && lastTocHashRef.current && currentHash !== lastTocHashRef.current) {
      console.log('TOC change detected, triggering sync');
      onTocChanged();
    }
    
    lastTocHashRef.current = currentHash;
  };

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
  }, [bookId, pollInterval, onTocChanged]);

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
