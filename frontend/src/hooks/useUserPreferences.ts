'use client';

import { useEffect, useState } from 'react';

import { useProfileApi, type UserPreferences } from '@/hooks/useProfileApi';

// Module-level cache: preference consumers (draft dialogs, export modal,
// editor auto-save) share one GET /users/me per page load instead of each
// fetching independently. The settings page invalidates on save. A failed or
// empty fetch is deliberately NOT cached so a later mount retries.
let cachedPreferences: UserPreferences | null = null;
let inflight: Promise<UserPreferences | null> | null = null;
// Bumped on invalidation so an older in-flight fetch can't clobber the
// fresher value the settings page just stored.
let generation = 0;

export function invalidateUserPreferencesCache(next?: UserPreferences | null): void {
  generation += 1;
  cachedPreferences = next ?? null;
  inflight = null;
}

/**
 * Read-only access to the signed-in user's stored preferences.
 * Returns null until loaded; consumers fall back to their own defaults, so a
 * failed fetch degrades to current shipped behavior rather than an error.
 */
export function useUserPreferences(): UserPreferences | null {
  const { getUserProfile } = useProfileApi();
  const [preferences, setPreferences] = useState<UserPreferences | null>(cachedPreferences);

  useEffect(() => {
    if (cachedPreferences) {
      setPreferences(cachedPreferences);
      return;
    }
    if (!inflight) {
      const startedAt = generation;
      inflight = getUserProfile()
        .then((profile) => profile?.preferences ?? null)
        .catch(() => null)
        .then((prefs) => {
          // Only the fetch matching the current generation may fill the cache.
          if (prefs && startedAt === generation) {
            cachedPreferences = prefs;
          }
          return prefs;
        })
        .finally(() => {
          inflight = null;
        });
    }
    let active = true;
    inflight.then((prefs) => {
      if (active && prefs) {
        setPreferences(prefs);
      }
    });
    return () => {
      active = false;
    };
  }, [getUserProfile]);

  return preferences;
}

export default useUserPreferences;
