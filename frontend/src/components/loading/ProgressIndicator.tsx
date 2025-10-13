import React from 'react';
import { cn } from '@/lib/utils';

/**
 * Props for the ProgressIndicator component
 */
export interface ProgressIndicatorProps {
  /**
   * Current progress count (e.g., 5 chapters processed)
   */
  current: number;

  /**
   * Total count (e.g., 10 total chapters)
   */
  total: number;

  /**
   * Unit name for the items being processed
   * @example "chapters", "pages", "items", "questions"
   */
  unit: string;

  /**
   * Whether to show percentage alongside the progress
   * @default true
   */
  showPercentage?: boolean;

  /**
   * Optional custom message to display
   * When not provided, uses "Processing {current} of {total} {unit}"
   */
  message?: string;

  /**
   * Additional CSS classes for the container
   */
  className?: string;

  /**
   * Size variant for the progress bar
   * @default "default"
   */
  size?: 'sm' | 'default' | 'lg';
}

/**
 * ProgressIndicator Component
 *
 * Displays visual progress feedback with:
 * - Progress bar with smooth transitions
 * - Text feedback ("Processing 5 of 10 chapters")
 * - Optional percentage display
 * - Accessible ARIA labels
 *
 * @example
 * ```tsx
 * <ProgressIndicator
 *   current={5}
 *   total={10}
 *   unit="chapters"
 *   showPercentage={true}
 * />
 * ```
 *
 * @example With custom message
 * ```tsx
 * <ProgressIndicator
 *   current={3}
 *   total={8}
 *   unit="pages"
 *   message="Generating content for page 3 of 8"
 * />
 * ```
 */
export function ProgressIndicator({
  current,
  total,
  unit,
  showPercentage = true,
  message,
  className,
  size = 'default',
}: ProgressIndicatorProps) {
  // Calculate percentage, ensuring it's between 0 and 100
  const percentage = total > 0 ? Math.min(Math.max((current / total) * 100, 0), 100) : 0;
  const roundedPercentage = Math.round(percentage);

  // Default message if none provided
  const displayMessage = message || `Processing ${current} of ${total} ${unit}`;

  // Size classes
  const heightClasses = {
    sm: 'h-1',
    default: 'h-2',
    lg: 'h-3',
  };

  const textClasses = {
    sm: 'text-xs',
    default: 'text-sm',
    lg: 'text-base',
  };

  return (
    <div
      className={cn('w-full space-y-2', className)}
      role="status"
      aria-live="polite"
    >
      {/* Progress text */}
      <div className={cn('flex justify-between items-center', textClasses[size])}>
        <span className="text-zinc-300 font-medium">
          {displayMessage}
        </span>
        {showPercentage && (
          <span className="text-zinc-400">
            {roundedPercentage}%
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div
        className={cn(
          'w-full bg-zinc-700 rounded-full overflow-hidden',
          heightClasses[size]
        )}
      >
        <div
          className={cn(
            'bg-indigo-600 rounded-full transition-all duration-500 ease-out',
            heightClasses[size]
          )}
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={roundedPercentage}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${displayMessage} - ${roundedPercentage}% complete`}
        />
      </div>

      {/* Numeric indicator */}
      <div className={cn('text-center text-zinc-500', textClasses[size])}>
        <span>
          {current} / {total}
        </span>
      </div>
    </div>
  );
}

/**
 * Compact variant with just the progress bar and percentage
 *
 * @example
 * ```tsx
 * <ProgressIndicator.Compact
 *   current={5}
 *   total={10}
 *   unit="chapters"
 * />
 * ```
 */
ProgressIndicator.Compact = function ProgressIndicatorCompact({
  current,
  total,
  unit,
  className,
}: ProgressIndicatorProps) {
  const percentage = total > 0 ? Math.min(Math.max((current / total) * 100, 0), 100) : 0;
  const roundedPercentage = Math.round(percentage);

  return (
    <div className={cn('flex items-center gap-3', className)} role="status">
      <div className="flex-1 bg-zinc-700 rounded-full h-1.5 overflow-hidden">
        <div
          className="bg-indigo-600 h-full rounded-full transition-all duration-500 ease-out"
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={roundedPercentage}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Processing ${current} of ${total} ${unit} - ${roundedPercentage}% complete`}
        />
      </div>
      <span className="text-xs text-zinc-400 whitespace-nowrap">
        {current}/{total}
      </span>
    </div>
  );
};
