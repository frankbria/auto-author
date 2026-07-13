'use client';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
import type { UserPreferences } from '@/hooks/useProfileApi';

type BooleanPreferenceKey =
  | 'email_notifications'
  | 'marketing_emails'
  | 'writing_reminders'
  | 'progress_updates'
  | 'backup_notifications';

const NOTIFICATION_TOGGLES: Array<{
  key: BooleanPreferenceKey;
  label: string;
  description: string;
  defaultValue: boolean;
}> = [
  {
    key: 'email_notifications',
    label: 'Email Notifications',
    description: 'Account updates and important activity on your books',
    defaultValue: true,
  },
  {
    key: 'marketing_emails',
    label: 'Marketing Emails',
    description: 'Product news, tips, and promotional content',
    defaultValue: false,
  },
  {
    key: 'writing_reminders',
    label: 'Writing Reminders',
    description: 'Nudges to keep a regular writing habit',
    defaultValue: false,
  },
  {
    key: 'progress_updates',
    label: 'Progress Updates',
    description: 'Milestone achievements as your book takes shape',
    defaultValue: true,
  },
  {
    key: 'backup_notifications',
    label: 'Backup Notifications',
    description: 'Alerts about local backups of unsaved work',
    defaultValue: true,
  },
];

interface NotificationSettingsFormProps {
  preferences: Partial<UserPreferences>;
  onChange: (partial: Partial<UserPreferences>) => void;
}

/**
 * Notification Settings tab: per-type email/notification toggles.
 * Controlled component — state lives in the settings page.
 *
 * Gated "coming soon" (#195): no notification-delivery infrastructure exists
 * yet, so every switch is hard-disabled. Stored preference values still render
 * and round-trip unchanged through the shared save flow.
 */
export default function NotificationSettingsForm({
  preferences,
  onChange,
}: NotificationSettingsFormProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <CardTitle>Notification Settings</CardTitle>
          <Badge variant="secondary">Coming soon</Badge>
        </div>
        <CardDescription>
          Notification delivery isn&apos;t available yet. Your saved choices will apply
          once notifications launch.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {NOTIFICATION_TOGGLES.map((toggle, index) => (
          <div key={toggle.key}>
            {index > 0 && <Separator className="mb-4" />}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor={`notification-${toggle.key}`}>{toggle.label}</Label>
                <p className="text-sm text-muted-foreground">{toggle.description}</p>
              </div>
              <Switch
                id={`notification-${toggle.key}`}
                checked={preferences[toggle.key] ?? toggle.defaultValue}
                onCheckedChange={(checked) => onChange({ [toggle.key]: checked })}
                disabled
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
