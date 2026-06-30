import { useCallback, useRef } from 'react';

interface SwipeGestureOptions {
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  /** Minimum horizontal distance (px) to count as a swipe. Default 50. */
  threshold?: number;
}

/**
 * Detect horizontal swipe gestures via native touch events. Returns a *callback
 * ref* to attach to the swipeable element. SSR-safe.
 *
 * A callback ref (not a ref object) is used deliberately: the swipeable element
 * is often mounted after the first render (e.g. ChapterTabs only renders the
 * swipe wrapper once `useMediaQuery` resolves to mobile). React invokes the
 * callback when the node attaches/detaches, so listeners bind at the right time
 * — a one-time effect keyed on an empty dep array would miss the late mount.
 *
 * Only fires when the gesture is predominantly horizontal (|dx| > |dy|), so it
 * does not hijack vertical scrolling or text selection.
 *
 * ponytail: distance + axis check is enough to tell a swipe from a scroll —
 * skipped velocity tracking; add it only if real devices misfire.
 */
export function useSwipeGesture<T extends HTMLElement = HTMLElement>({
  onSwipeLeft,
  onSwipeRight,
  threshold = 50,
}: SwipeGestureOptions) {
  // Keep the latest callbacks without re-binding listeners every render.
  const latest = useRef({ onSwipeLeft, onSwipeRight, threshold });
  latest.current = { onSwipeLeft, onSwipeRight, threshold };

  const cleanupRef = useRef<(() => void) | null>(null);

  return useCallback((node: T | null) => {
    // Detach from any previously-attached node first.
    if (cleanupRef.current) {
      cleanupRef.current();
      cleanupRef.current = null;
    }
    if (!node || typeof window === 'undefined') return;

    let startX = 0;
    let startY = 0;
    let tracking = false;

    const onTouchStart = (e: TouchEvent) => {
      const t = e.touches[0];
      if (!t) return;
      startX = t.clientX;
      startY = t.clientY;
      tracking = true;
    };

    const onTouchEnd = (e: TouchEvent) => {
      if (!tracking) return;
      tracking = false;
      const t = e.changedTouches[0];
      if (!t) return;
      const dx = t.clientX - startX;
      const dy = t.clientY - startY;
      const { threshold: th, onSwipeLeft: left, onSwipeRight: right } = latest.current;
      // Horizontal swipe only: past threshold and more horizontal than vertical.
      if (Math.abs(dx) < th || Math.abs(dx) <= Math.abs(dy)) return;
      if (dx < 0) left?.();
      else right?.();
    };

    node.addEventListener('touchstart', onTouchStart, { passive: true });
    node.addEventListener('touchend', onTouchEnd, { passive: true });
    cleanupRef.current = () => {
      node.removeEventListener('touchstart', onTouchStart);
      node.removeEventListener('touchend', onTouchEnd);
    };
  }, []);
}
