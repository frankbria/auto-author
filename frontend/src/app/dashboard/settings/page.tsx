'use client';

import { useSession } from '@/lib/auth-client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { useCallback, useEffect, useState } from 'react';
import { toast } from '@/lib/toast';
import { useAuthFetch } from '@/hooks/useAuthFetch';

interface UserPreferences {
  theme?: string;
  email_notifications?: boolean;
  marketing_emails?: boolean;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export default function SettingsPage() {
  const { data: session } = useSession();
  const user = session?.user;
  const { authFetch } = useAuthFetch({ baseUrl: API_BASE_URL });
  const [emailNotifications, setEmailNotifications] = useState(true);
  // ponytail: auto-save is a client-only preference; backend has no field for it.
  const [autoSave, setAutoSave] = useState(true);
  const [darkMode, setDarkMode] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  // 'loading' | 'loaded' | 'error'. Saving is only allowed after a successful load
  // so a failed/partial load can't overwrite persisted preferences with UI defaults.
  const [loadState, setLoadState] = useState<'loading' | 'loaded' | 'error'>('loading');
  // Preserve preference fields the UI doesn't expose (e.g. marketing_emails) so Save doesn't reset them.
  const [loadedPreferences, setLoadedPreferences] = useState<UserPreferences>({});

  const loadPreferences = useCallback(() => {
    let active = true;
    setLoadState('loading');
    authFetch<{ preferences?: UserPreferences }>('/users/me')
      .then((data) => {
        if (!active) return;
        const prefs = data?.preferences ?? {};
        setLoadedPreferences(prefs);
        if (prefs.theme) {
          setDarkMode(prefs.theme === 'dark');
        }
        if (typeof prefs.email_notifications === 'boolean') {
          setEmailNotifications(prefs.email_notifications);
        }
        setLoadState('loaded');
      })
      .catch(() => {
        // Do NOT enable saving: saving now would overwrite persisted fields with defaults.
        if (active) setLoadState('error');
      });
    return () => {
      active = false;
    };
  }, [authFetch]);

  useEffect(() => loadPreferences(), [loadPreferences]);

  const isLoaded = loadState === 'loaded';

  const handleSaveSettings = async () => {
    setIsSaving(true);
    try {
      await authFetch('/users/me', {
        method: 'PATCH',
        body: JSON.stringify({
          preferences: {
            ...loadedPreferences,
            theme: darkMode ? 'dark' : 'light',
            email_notifications: emailNotifications,
          },
        }),
      });
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
      <h1 className="text-3xl font-bold mb-8">Settings</h1>

      <div className="space-y-6">
        {/* Profile Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Profile Settings</CardTitle>
            <CardDescription>Manage your account information</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={user?.email || ''}
                disabled
              />
              <p className="text-sm text-muted-foreground">
                Email cannot be changed here. Update it in your account settings.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="name">Display Name</Label>
              <Input
                id="name"
                value={user?.name || ''}
                disabled
              />
            </div>
          </CardContent>
        </Card>

        {/* Preferences */}
        <Card>
          <CardHeader>
            <CardTitle>Preferences</CardTitle>
            <CardDescription>Customize your writing experience</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="email-notifications">Email Notifications</Label>
                <p className="text-sm text-muted-foreground">
                  Receive updates about your books and writing progress
                </p>
              </div>
              <Switch
                id="email-notifications"
                checked={emailNotifications}
                onCheckedChange={setEmailNotifications}
                disabled={!isLoaded}
              />
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="auto-save">Auto-save</Label>
                <p className="text-sm text-muted-foreground">
                  Automatically save your work while editing
                </p>
              </div>
              <Switch
                id="auto-save"
                checked={autoSave}
                onCheckedChange={setAutoSave}
              />
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="dark-mode">Dark Mode</Label>
                <p className="text-sm text-muted-foreground">
                  Use dark theme for reduced eye strain
                </p>
              </div>
              <Switch
                id="dark-mode"
                checked={darkMode}
                onCheckedChange={setDarkMode}
                disabled={!isLoaded}
              />
            </div>
          </CardContent>
        </Card>

        {/* Writing Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Writing Settings</CardTitle>
            <CardDescription>Configure your writing environment</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="auto-save-interval">Auto-save Interval (seconds)</Label>
              <Input
                id="auto-save-interval"
                type="number"
                min="1"
                max="300"
                defaultValue="3"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="default-font-size">Editor Font Size</Label>
              <select
                id="default-font-size"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                defaultValue="16"
              >
                <option value="14">Small (14px)</option>
                <option value="16">Medium (16px)</option>
                <option value="18">Large (18px)</option>
                <option value="20">Extra Large (20px)</option>
              </select>
            </div>
          </CardContent>
        </Card>

        {/* Load error — saving stays disabled so we can't overwrite stored preferences with defaults */}
        {loadState === 'error' && (
          <div
            role="alert"
            className="flex items-center justify-between rounded-md bg-destructive/10 p-3 text-sm text-destructive"
          >
            <span>Couldn&apos;t load your current preferences. Saving is disabled to avoid overwriting them.</span>
            <Button variant="outline" size="sm" onClick={loadPreferences}>
              Retry
            </Button>
          </div>
        )}

        {/* Save Button */}
        <div className="flex justify-end">
          <Button onClick={handleSaveSettings} size="lg" disabled={isSaving || !isLoaded}>
            {isSaving ? 'Saving...' : loadState === 'loading' ? 'Loading...' : 'Save Settings'}
          </Button>
        </div>
      </div>
    </div>
  );
}
