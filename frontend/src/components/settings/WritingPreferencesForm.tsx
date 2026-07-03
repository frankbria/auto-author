'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { WRITING_STYLES } from '@/lib/constants/writing-styles';
import {
  AUTO_SAVE_MAX_SECONDS,
  AUTO_SAVE_MIN_SECONDS,
  isValidAutoSaveInterval,
} from '@/lib/constants/auto-save';
import type { UserPreferences } from '@/hooks/useProfileApi';

export { isValidAutoSaveInterval };

interface WritingPreferencesFormProps {
  preferences: Partial<UserPreferences>;
  onChange: (partial: Partial<UserPreferences>) => void;
  disabled?: boolean;
}

/**
 * Writing Preferences tab: default AI writing style, auto-save frequency,
 * and editor theme. Controlled component — state lives in the settings page.
 */
export default function WritingPreferencesForm({
  preferences,
  onChange,
  disabled = false,
}: WritingPreferencesFormProps) {
  const interval = preferences.auto_save_interval ?? AUTO_SAVE_MIN_SECONDS;
  const intervalInvalid = !isValidAutoSaveInterval(interval);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Writing Preferences</CardTitle>
        <CardDescription>Defaults for AI drafting and the chapter editor</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="default-writing-style">Default Writing Style</Label>
          <select
            id="default-writing-style"
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            value={preferences.default_writing_style ?? 'conversational'}
            onChange={(e) =>
              onChange({
                default_writing_style: e.target.value as UserPreferences['default_writing_style'],
              })
            }
            disabled={disabled}
          >
            {WRITING_STYLES.map((style) => (
              <option key={style.value} value={style.value}>
                {style.label}
              </option>
            ))}
          </select>
          <p className="text-sm text-muted-foreground">
            Pre-selected when generating chapter drafts with AI
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="auto-save-interval">Auto-save Interval (seconds)</Label>
          <Input
            id="auto-save-interval"
            type="number"
            min={AUTO_SAVE_MIN_SECONDS}
            max={AUTO_SAVE_MAX_SECONDS}
            value={Number.isNaN(interval) ? '' : interval}
            onChange={(e) => onChange({ auto_save_interval: e.target.valueAsNumber })}
            disabled={disabled}
            aria-invalid={intervalInvalid}
            aria-describedby="auto-save-interval-help"
          />
          <p
            id="auto-save-interval-help"
            className={`text-sm ${intervalInvalid ? 'text-destructive' : 'text-muted-foreground'}`}
            role={intervalInvalid ? 'alert' : undefined}
          >
            {intervalInvalid
              ? `Must be a whole number between ${AUTO_SAVE_MIN_SECONDS} and ${AUTO_SAVE_MAX_SECONDS} seconds`
              : 'How often the chapter editor saves your work'}
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="editor-theme">Editor Theme</Label>
          <select
            id="editor-theme"
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            value={preferences.theme ?? 'system'}
            onChange={(e) => onChange({ theme: e.target.value as UserPreferences['theme'] })}
            disabled={disabled}
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="system">System</option>
          </select>
          <p className="text-sm text-muted-foreground">Applied immediately across the app</p>
        </div>
      </CardContent>
    </Card>
  );
}
