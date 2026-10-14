'use client';

import * as RadioGroupPrimitive from '@radix-ui/react-radio-group';

export type ExportFormatChoice = {
  format: string;
  name: string;
  description: string;
  icon: string;
  extension: string;
  available: boolean;
};

interface ExportFormatPickerProps {
  formats: ExportFormatChoice[];
  value: string;
  onChange: (format: string) => void;
  /** id of the heading that names the group */
  labelledBy: string;
}

/**
 * The export page's format cards, as one radio group: a single tab stop, the
 * arrow keys choose, and a format the server cannot make is passed over (#836).
 */
export function ExportFormatPicker({ formats, value, onChange, labelledBy }: ExportFormatPickerProps) {
  return (
    <RadioGroupPrimitive.Root
      value={value}
      onValueChange={onChange}
      aria-labelledby={labelledBy}
      className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4"
    >
      {formats.map(format => (
        <RadioGroupPrimitive.Item
          key={format.format}
          value={format.format}
          disabled={!format.available}
          aria-disabled={!format.available}
          aria-labelledby={`export-format-${format.format}-name`}
          aria-describedby={`export-format-${format.format}-description`}
          className={`text-left border rounded-lg p-4 transition-colors focus-visible:outline-hidden focus-visible:ring-[3px] focus-visible:ring-ring disabled:opacity-50 disabled:cursor-not-allowed ${
            value === format.format
              ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-900/20'
              : 'border-border hover:bg-secondary/50'
          }`}
        >
          <span className="flex items-center mb-2">
            <span aria-hidden="true" className="text-2xl mr-3">{format.icon}</span>
            <span className="flex-1">
              <span id={`export-format-${format.format}-name`} className="block font-medium text-foreground">{format.name}</span>
              <span className="block text-muted-foreground text-xs">{format.extension}</span>
            </span>
            <span aria-hidden="true" className={`w-4 h-4 shrink-0 rounded-full ${value === format.format ? 'bg-indigo-500' : 'bg-secondary'}`}></span>
          </span>
          <span id={`export-format-${format.format}-description`} className="block text-muted-foreground text-sm">{format.description}</span>
        </RadioGroupPrimitive.Item>
      ))}
    </RadioGroupPrimitive.Root>
  );
}
