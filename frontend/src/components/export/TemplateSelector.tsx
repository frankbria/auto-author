'use client';

import { useState } from 'react';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Badge } from '@/components/ui/badge';
import { ExportTemplate, TemplateCustomization } from '@/types/export';

const DEFAULT_OPTION = '__default__';

interface TemplateSelectorProps {
  /** Templates available for this book (from the export formats/templates API) */
  templates: ExportTemplate[];
  /** Currently selected template id; undefined means "Default formatting" */
  selectedTemplateId?: string;
  /** Called with the chosen template id (undefined = default formatting) */
  onSelect: (templateId: string | undefined) => void;
  /** Current customization overrides */
  customization?: TemplateCustomization;
  /** Called when customization changes */
  onCustomizationChange?: (customization: TemplateCustomization) => void;
}

/**
 * Professional export template picker (issue #59).
 *
 * Shows a "Default formatting" option plus every available template as a
 * selectable card. Selecting a template reveals an inline spec preview (page
 * size, margins, font, spacing) and a small customization panel for overriding
 * font size and margins — satisfying "preview before export" and "templates
 * support customization" without a separate preview modal.
 */
export function TemplateSelector({
  templates,
  selectedTemplateId,
  onSelect,
  customization,
  onCustomizationChange,
}: TemplateSelectorProps) {
  const [showCustomize, setShowCustomize] = useState(false);

  const selected = templates.find((t) => t.id === selectedTemplateId);

  const updateCustomization = (patch: TemplateCustomization) => {
    onCustomizationChange?.({ ...customization, ...patch });
  };

  return (
    <div className="space-y-3" data-testid="template-selector">
      <Label className="text-base font-semibold">Template</Label>

      <RadioGroup
        value={selectedTemplateId ?? DEFAULT_OPTION}
        onValueChange={(value) =>
          onSelect(value === DEFAULT_OPTION ? undefined : value)
        }
      >
        {/* Default (legacy) formatting */}
        <div className="flex items-start space-x-3 space-y-0 rounded-md border p-3 hover:bg-accent">
          <RadioGroupItem value={DEFAULT_OPTION} id="template-default" />
          <div className="flex-1">
            <Label htmlFor="template-default" className="font-medium cursor-pointer">
              Default formatting
            </Label>
            <p className="text-sm text-muted-foreground mt-1">
              Standard layout — no professional template applied.
            </p>
          </div>
        </div>

        {templates.map((template) => (
          <div
            key={template.id}
            className="flex items-start space-x-3 space-y-0 rounded-md border p-3 hover:bg-accent"
            data-testid={`template-option-${template.id}`}
          >
            <RadioGroupItem value={template.id} id={`template-${template.id}`} />
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <Label
                  htmlFor={`template-${template.id}`}
                  className="font-medium cursor-pointer"
                >
                  {template.name}
                </Label>
                {template.category && (
                  <Badge variant="secondary" className="text-xs">
                    {template.category}
                  </Badge>
                )}
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                {template.description}
              </p>
              {template.best_for && (
                <p className="text-xs text-muted-foreground mt-1">
                  Best for: {template.best_for}
                </p>
              )}
            </div>
          </div>
        ))}
      </RadioGroup>

      {/* Inline spec preview for the selected template */}
      {selected && (
        <div
          className="rounded-lg bg-muted p-4 space-y-1.5 text-sm"
          data-testid="template-preview"
        >
          <p className="font-semibold">{selected.name} — preview</p>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Page size</span>
            <span className="font-medium">{selected.page_size}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Margins (in)</span>
            <span className="font-medium">
              {customization?.margins?.top ?? selected.margins.top} top ·{' '}
              {customization?.margins?.inside ?? selected.margins.inside} inside ·{' '}
              {customization?.margins?.outside ?? selected.margins.outside} outside
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Font</span>
            <span className="font-medium">
              {selected.font.docx_font},{' '}
              {customization?.font_size ?? selected.font.size}pt
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Line spacing</span>
            <span className="font-medium">
              {customization?.line_height ?? selected.line_height}×
            </span>
          </div>

          <div className="pt-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setShowCustomize((v) => !v)}
              data-testid="customize-toggle"
            >
              {showCustomize ? 'Hide customization' : 'Customize'}
            </Button>
          </div>

          {showCustomize && (
            <div className="grid grid-cols-2 gap-3 pt-2" data-testid="template-customization">
              <div className="space-y-1">
                <Label htmlFor="custom-font-size" className="text-xs">
                  Font size (pt)
                </Label>
                <Input
                  id="custom-font-size"
                  type="number"
                  min={8}
                  max={18}
                  value={customization?.font_size ?? selected.font.size}
                  onChange={(e) =>
                    updateCustomization({ font_size: Number(e.target.value) })
                  }
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="custom-inside-margin" className="text-xs">
                  Inside margin (in)
                </Label>
                <Input
                  id="custom-inside-margin"
                  type="number"
                  min={0.25}
                  max={2}
                  step={0.05}
                  value={customization?.margins?.inside ?? selected.margins.inside}
                  onChange={(e) =>
                    updateCustomization({
                      margins: {
                        ...customization?.margins,
                        inside: Number(e.target.value),
                      },
                    })
                  }
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
