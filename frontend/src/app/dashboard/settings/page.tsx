'use client';

import Link from 'next/link';
import { useTheme } from 'next-themes';
import { useCallback, useEffect, useState } from 'react';

import ExportSettingsForm from '@/components/settings/ExportSettingsForm';
import NotificationSettingsForm from '@/components/settings/NotificationSettingsForm';
import SecuritySettingsForm from '@/components/settings/SecuritySettingsForm';
import WritingPreferencesForm, {
  isValidAutoSaveInterval,
} from '@/components/settings/WritingPreferencesForm';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useProfileApi, type UserPreferences } from '@/hooks/useProfileApi';
import { invalidateUserPreferencesCache } from '@/hooks/useUserPreferences';
import { toast } from '@/lib/toast';

export default function SettingsPage() {
  const { getUserProfile, updateUserProfile } = useProfileApi();
  const { setTheme } = useTheme();
  const [activeTab, setActiveTab] = useState('writing');
  const [isSaving, setIsSaving] = useState(false);
  // 'loading' | 'loaded' | 'error'. Saving is only allowed after a successful load
  // so a failed/partial load can't overwrite persisted preferences with UI defaults.
  const [loadState, setLoadState] = useState<'loading' | 'loaded' | 'error'>('loading');
  // Full preferences object from the server, merged with edits before every save so
  // fields this page doesn't expose are never reset (PATCH replaces the whole object).
  const [preferences, setPreferences] = useState<Partial<UserPreferences>>({});

  const loadPreferences = useCallback(() => {
    let active = true;
    setLoadState('loading');
    getUserProfile()
      .then((profile) => {
        if (!active) return;
        setPreferences(profile?.preferences ?? {});
        setLoadState('loaded');
      })
      .catch(() => {
        // Do NOT enable saving: saving now would overwrite persisted fields with defaults.
        if (active) setLoadState('error');
      });
    return () => {
      active = false;
    };
  }, [getUserProfile]);

  useEffect(() => loadPreferences(), [loadPreferences]);

  const isLoaded = loadState === 'loaded';
  const intervalValid = isValidAutoSaveInterval(preferences.auto_save_interval ?? 3);

  const handlePreferencesChange = (partial: Partial<UserPreferences>) => {
    setPreferences((prev) => ({ ...prev, ...partial }));
    // Editor theme applies immediately across the app (next-themes); it is
    // persisted server-side when the user saves.
    if (partial.theme) {
      setTheme(partial.theme);
    }
  };

  const handleSaveSettings = async () => {
    setIsSaving(true);
    try {
      const updated = await updateUserProfile({
        preferences: preferences as UserPreferences,
      });
      if (updated?.preferences) {
        setPreferences(updated.preferences);
      }
      // Draft/export/editor consumers read a cached copy — refresh it.
      invalidateUserPreferencesCache(updated?.preferences ?? null);
      toast({
        title: 'Settings saved',
        description: 'Your preferences have been updated successfully.',
      });
    } catch (err) {
      toast({
        title: 'Save failed',
        description: err instanceof Error ? err.message : 'Could not update your preferences.',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="container mx-auto py-8 max-w-2xl">
      <div className="mb-8 flex items-end justify-between">
        <h1 className="text-3xl font-bold">Settings</h1>
        <Link href="/profile" className="text-sm text-muted-foreground underline-offset-4 hover:underline">
          Edit profile
        </Link>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-6 w-full">
          <TabsTrigger value="writing">Writing</TabsTrigger>
          <TabsTrigger value="export">Export</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
        </TabsList>

        {loadState === 'loading' && activeTab !== 'security' ? (
          <div role="status" aria-busy="true" className="space-y-4">
            <span className="sr-only">Loading your preferences…</span>
            <Skeleton className="h-48 w-full" />
            <Skeleton className="h-10 w-32 ml-auto" />
          </div>
        ) : (
          <>
            <TabsContent value="writing">
              <WritingPreferencesForm
                preferences={preferences}
                onChange={handlePreferencesChange}
                disabled={!isLoaded}
              />
            </TabsContent>
            <TabsContent value="export">
              <ExportSettingsForm
                preferences={preferences}
                onChange={handlePreferencesChange}
                disabled={!isLoaded}
              />
            </TabsContent>
            <TabsContent value="notifications">
              <NotificationSettingsForm
                preferences={preferences}
                onChange={handlePreferencesChange}
                disabled={!isLoaded}
              />
            </TabsContent>
          </>
        )}

        <TabsContent value="security">
          <SecuritySettingsForm />
        </TabsContent>
      </Tabs>

      {/* Load error — saving stays disabled so we can't overwrite stored preferences with defaults */}
      {loadState === 'error' && activeTab !== 'security' && (
        <div
          role="alert"
          className="mt-6 flex items-center justify-between rounded-md bg-destructive/10 p-3 text-sm text-destructive"
        >
          <span>Couldn&apos;t load your current preferences. Saving is disabled to avoid overwriting them.</span>
          <Button variant="outline" size="sm" onClick={loadPreferences}>
            Retry
          </Button>
        </div>
      )}

      {/* Security actions save themselves; the shared button covers preference tabs */}
      {activeTab !== 'security' && (
        <div className="mt-6 flex justify-end">
          <Button
            onClick={handleSaveSettings}
            size="lg"
            disabled={isSaving || !isLoaded || !intervalValid}
          >
            {isSaving ? 'Saving...' : loadState === 'loading' ? 'Loading...' : 'Save Settings'}
          </Button>
        </div>
      )}
    </div>
  );
}
