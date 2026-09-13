'use client';

import { useEffect, useSyncExternalStore } from 'react';

import { useProfileApi, type UserPreferences } from '@/hooks/useProfileApi';

// Module-level cache: preference consumers (draft dialogs, export modal,
// editor auto-save) share one GET /users/me per page load instead of each
// fetching independently. The settings page invalidates on save. A failed or
// empty fetch is deliberately NOT cached so a later mount retries.
//
// This is an external store, so `useSyncExternalStore` reads it rather than an
// effect mirroring it into component state (#584). The mirror was not just an
// extra render: a consumer already mounted when the settings page called
// `invalidateUserPreferencesCache(updated)` never saw the new value, because
// its effect had already run and nothing re-ran it. Subscribers fix that.
let cachedPreferences: UserPreferences | null = null;
let inflight: Promise<UserPreferences | null> | null = null;
// Bumped on invalidation so an older in-flight fetch can't clobber the
// fresher value the settings page just stored.
let generation = 0;

const listeners = new Set<() => void>();

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function publish(next: UserPreferences | null): void {
  // Identity is the change signal for useSyncExternalStore, so only notify on
  // a real swap — re-publishing the same reference would be a no-op anyway.
  if (cachedPreferences === next) return;
  cachedPreferences = next;
  listeners.forEach((listener) => listener());
}

/** getSnapshot must be referentially stable between notifications. */
const getSnapshot = (): UserPreferences | null => cachedPreferences;
/** Server render has no cache; matches the old `useState(null)` first paint. */
const getServerSnapshot = (): UserPreferences | null => null;

export function invalidateUserPreferencesCache(next?: UserPreferences | null): void {
  generation += 1;
  inflight = null;
  publish(next ?? null);
}

/**
 * Read-only access to the signed-in user's stored preferences.
 * Returns null until loaded; consumers fall back to their own defaults, so a
 * failed fetch degrades to current shipped behavior rather than an error.
 */
export function useUserPreferences(): UserPreferences | null {
  const { getUserProfile } = useProfileApi();
  const preferences = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  useEffect(() => {
    if (cachedPreferences || inflight) return;
    const startedAt = generation;
    inflight = getUserProfile()
      .then((profile) => profile?.preferences ?? null)
      .catch(() => null)
      .then((prefs) => {
        // Only the fetch matching the current generation may fill the cache.
        if (prefs && startedAt === generation) {
          publish(prefs);
        }
        return prefs;
      })
      .finally(() => {
        if (startedAt === generation) {
          inflight = null;
        }
      });
  }, [getUserProfile]);

  return preferences;
}

export default useUserPreferences;
