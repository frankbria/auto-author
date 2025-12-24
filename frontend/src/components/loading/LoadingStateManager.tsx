import React, { useEffect, useState } from 'react';
import { HugeiconsIcon } from '@hugeicons/react';
import { Loading03Icon, Cancel01Icon } from '@hugeicons/core-free-icons';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

/**
 * Props for the LoadingStateManager component
 */
export interface LoadingStateManagerProps {
  /**
   * Whether the loading state is active
   */
  isLoading: boolean;

  /**
   * The name of the operation being performed
   * @example "Generating table of contents"
   */
  operation: string;

  /**
   * Optional progress percentage (0-100)
   * When provided, displays a progress bar
   */
  progress?: number;

  /**
   * Optional estimated time remaining in milliseconds
   * When provided, displays a countdown timer
   */
  estimatedTime?: number;

  /**
   * Optional detailed message about the current operation
   * @example "Analyzing your summary and generating chapter structure..."
   */
  message?: string;

  /**
   * Optional callback when user cancels the operation
   * When provided, displays a cancel button
   */
  onCancel?: () => void;

  /**
   * Additional CSS classes for the container
   */
  className?: string;

  /**
   * Whether to show the loading state inline (smaller) or full-screen
   * @default false
   */
  inline?: boolean;
}

/**
 * LoadingStateManager Component
 *
 * A comprehensive loading indicator with support for:
 * - Progress bars with percentage
 * - Time estimates with countdown
 * - Cancellable operations
 * - Accessible ARIA labels
 * - Graceful transitions (fade in after 200ms to avoid flicker)
 *
 * @example
 * ```tsx
 * <LoadingStateManager
 *   isLoading={isGenerating}
 *   operation="Generating table of contents"
 *   progress={progress}
 *   estimatedTime={15000} // 15 seconds
 *   message="Analyzing your summary and generating chapter structure..."
 *   onCancel={() => setIsGenerating(false)}
 * />
 * ```
 */
export function LoadingStateManager({
  isLoading,
  operation,
  progress,
  estimatedTime,
  message,
  onCancel,
  className,
  inline = false,
}: LoadingStateManagerProps) {
  const [visible, setVisible] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState(estimatedTime);

  // Delay showing the loading state to avoid flicker for very fast operations
  useEffect(() => {
    if (isLoading) {
      const timer = setTimeout(() => setVisible(true), 200);
      return () => clearTimeout(timer);
    } else {
      setVisible(false);
    }
  }, [isLoading]);

  // Countdown timer for estimated time
  useEffect(() => {
    if (!isLoading || !estimatedTime) {
      setTimeRemaining(estimatedTime);
      return;
    }

    setTimeRemaining(estimatedTime);
    const interval = setInterval(() => {
      setTimeRemaining((prev) => {
        if (!prev || prev <= 0) return 0;
        return prev - 100;
      });
    }, 100);

    return () => clearInterval(interval);
  }, [isLoading, estimatedTime]);

  if (!isLoading || !visible) {
    return null;
  }

  const timeInSeconds = timeRemaining ? Math.ceil(timeRemaining / 1000) : 0;
  const hasProgress = typeof progress === 'number';
  const progressValue = hasProgress ? Math.min(Math.max(progress, 0), 100) : 0;

  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy="true"
      className={cn(
        'flex flex-col items-center justify-center space-y-4 p-6 transition-opacity duration-300',
        inline ? 'py-4' : 'min-h-[200px]',
        className
      )}
    >
      {/* Spinner */}
      <div className="relative">
        <HugeiconsIcon
          icon={Loading03Icon}
          size={inline ? 32 : 48}
          className={cn(
            "animate-spin text-indigo-500",
            inline ? "h-8 w-8" : "h-12 w-12"
          )}
          aria-label={`Loading: ${operation}`}
        />
      </div>

      {/* Operation name */}
      <div className="text-center space-y-2">
        <h3
          className={cn(
            'font-medium text-zinc-100',
            inline ? 'text-base' : 'text-lg'
          )}
        >
          {operation}
        </h3>

        {/* Detailed message */}
        {message && (
          <p className="text-sm text-zinc-400 max-w-md">
            {message}
          </p>
        )}
      </div>

      {/* Progress bar */}
      {hasProgress && (
        <div className="w-full max-w-md space-y-2">
          <div className="flex justify-between text-xs text-zinc-400">
            <span>{progressValue}% complete</span>
            {timeRemaining && timeRemaining > 0 && (
              <span>~{timeInSeconds}s remaining</span>
            )}
          </div>
          <div className="w-full bg-zinc-700 rounded-full h-2 overflow-hidden">
            <div
              className="bg-indigo-600 h-full rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progressValue}%` }}
              role="progressbar"
              aria-valuenow={progressValue}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`${operation} progress`}
            />
          </div>
        </div>
      )}

      {/* Time estimate (without progress bar) */}
      {!hasProgress && timeRemaining && timeRemaining > 0 && (
        <p className="text-sm text-zinc-400">
          Estimated time: ~{timeInSeconds} second{timeInSeconds !== 1 ? 's' : ''}
        </p>
      )}

      {/* Cancel button */}
      {onCancel && (
        <Button
          variant="outline"
          size="sm"
          onClick={onCancel}
          className="mt-2"
          aria-label={`Cancel ${operation}`}
        >
          <HugeiconsIcon icon={Cancel01Icon} size={16} className="mr-2" />
          Cancel
        </Button>
      )}
    </div>
  );
}
