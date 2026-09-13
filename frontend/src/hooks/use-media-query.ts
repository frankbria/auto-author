import { useCallback, useSyncExternalStore } from 'react';

/**
 * Subscribe to a CSS media query.
 *
 * Uses `useSyncExternalStore` rather than `useState` + an effect (#584,
 * react-hooks/set-state-in-effect). `matchMedia` is an external store, which is
 * exactly what this hook is for: the previous shape read `media.matches` inside
 * an effect and pushed it into state, costing a second render on mount and
 * leaving one frame where the value was `false` on the client even though the
 * query already matched.
 *
 * `getServerSnapshot` returns `false`, matching the old `useState(false)` initial
 * value, so server output and the first client render still agree.
 */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onChange: () => void) => {
      const media = window.matchMedia(query);
      media.addEventListener('change', onChange);
      return () => media.removeEventListener('change', onChange);
    },
    [query]
  );

  return useSyncExternalStore(
    subscribe,
    () => window.matchMedia(query).matches,
    () => false
  );
}
