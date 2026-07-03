'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Switch } from '@/components/ui/switch';
import type { UserPreferences } from '@/hooks/useProfileApi';

const EXPORT_FORMATS: Array<{
  value: NonNullable<UserPreferences['default_export_format']>;
  label: string;
}> = [
  { value: 'pdf', label: 'PDF' },
  { value: 'docx', label: 'DOCX' },
  { value: 'epub', label: 'EPUB' },
  { value: 'markdown', label: 'Markdown' },
];

interface ExportSettingsFormProps {
  preferences: Partial<UserPreferences>;
  onChange: (partial: Partial<UserPreferences>) => void;
  disabled?: boolean;
}

/**
 * Export Settings tab: default format, page size (PDF only), and the
 * include-empty-chapters default. Controlled component.
 */
export default function ExportSettingsForm({
  preferences,
  onChange,
  disabled = false,
}: ExportSettingsFormProps) {
  const format = preferences.default_export_format ?? 'pdf';

  return (
    <Card>
      <CardHeader>
        <CardTitle>Export Settings</CardTitle>
        <CardDescription>Defaults pre-selected in the export dialog</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-3">
          <Label id="default-export-format-label">Default Export Format</Label>
          <RadioGroup
            aria-labelledby="default-export-format-label"
            value={format}
            onValueChange={(value) =>
              onChange({
                default_export_format: value as UserPreferences['default_export_format'],
              })
            }
            disabled={disabled}
            className="grid grid-cols-2 gap-2"
          >
            {EXPORT_FORMATS.map((f) => (
              <div key={f.value} className="flex items-center gap-2">
                <RadioGroupItem value={f.value} id={`export-format-${f.value}`} />
                <Label htmlFor={`export-format-${f.value}`}>{f.label}</Label>
              </div>
            ))}
          </RadioGroup>
        </div>

        {format === 'pdf' && (
          <div className="space-y-3">
            <Label id="default-page-size-label">Page Size</Label>
            <RadioGroup
              aria-labelledby="default-page-size-label"
              value={preferences.default_page_size ?? 'letter'}
              onValueChange={(value) =>
                onChange({ default_page_size: value as UserPreferences['default_page_size'] })
              }
              disabled={disabled}
              className="flex gap-6"
            >
              <div className="flex items-center gap-2">
                <RadioGroupItem value="letter" id="page-size-letter" />
                <Label htmlFor="page-size-letter">Letter</Label>
              </div>
              <div className="flex items-center gap-2">
                <RadioGroupItem value="A4" id="page-size-a4" />
                <Label htmlFor="page-size-a4">A4</Label>
              </div>
            </RadioGroup>
          </div>
        )}

        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="include-empty-chapters">Include Empty Chapters</Label>
            <p className="text-sm text-muted-foreground">
              Export chapters that have no content yet
            </p>
          </div>
          <Switch
            id="include-empty-chapters"
            checked={preferences.include_empty_chapters ?? false}
            onCheckedChange={(checked) => onChange({ include_empty_chapters: checked })}
            disabled={disabled}
          />
        </div>
      </CardContent>
    </Card>
  );
}
