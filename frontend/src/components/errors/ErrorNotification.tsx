'use client';

import { toast } from 'sonner';
import { ClassifiedError, ErrorType } from '@/lib/errors';
import { HugeiconsIcon } from '@hugeicons/react';
import { AlertCircleIcon, RefreshIcon, Cancel01Icon, Clock01Icon, Database01Icon } from '@hugeicons/core-free-icons';
import { Button } from '@/components/ui/button';
import { navigateTo } from '@/lib/navigation';
import { useEffect, useState } from 'react';

/**
 * Error notification props
 */
export interface ErrorNotificationProps {
  /** Classified error to display */
  error: ClassifiedError;
  /** Callback when user clicks retry button */
  onRetry?: () => void;
  /** Callback when notification is dismissed */
  onDismiss?: () => void;
  /** Custom duration in milliseconds (default: based on error type) */
  duration?: number;
  /** Whether this is showing cached content */
  isFromCache?: boolean;
  /** Estimated seconds until retry is available */
  retryAfter?: number;
}

/**
 * Countdown timer component for retry after
 */
function RetryCountdown({ initialSeconds, onRetry }: { initialSeconds: number; onRetry: () => void }) {
  const [secondsLeft, setSecondsLeft] = useState(initialSeconds);

  useEffect(() => {
    if (secondsLeft <= 0) return;

    const timer = setInterval(() => {
      setSecondsLeft(prev => Math.max(0, prev - 1));
    }, 1000);

    return () => clearInterval(timer);
  }, [secondsLeft]);

  const minutes = Math.floor(secondsLeft / 60);
  const seconds = secondsLeft % 60;

  return (
    <div className="flex items-center gap-2 text-sm">
      <HugeiconsIcon icon={Clock01Icon} size={16} />
      <span>
        {secondsLeft > 0 ? (
          `Retry in ${minutes}:${seconds.toString().padStart(2, '0')}`
        ) : (
          <Button size="sm" variant="outline" onClick={onRetry}>
            <HugeiconsIcon icon={RefreshIcon} size={12} className="mr-1" />
            Retry Now
          </Button>
        )}
      </span>
    </div>
  );
}

/**
 * Show an error notification using the toast system
 *
 * @param error - Classified error to display
 * @param options - Notification options
 */
export function showErrorNotification(
  error: ClassifiedError,
  options: {
    onRetry?: () => void;
    onDismiss?: () => void;
    duration?: number;
    isFromCache?: boolean;
    retryAfter?: number;
  } = {}
) {
  const { onRetry, onDismiss, duration, isFromCache, retryAfter } = options;

  // Determine default duration based on error type
  const defaultDuration =
    duration ||
    (error.type === ErrorType.TRANSIENT ? 5000 :
     error.type === ErrorType.AI_SERVICE ? (isFromCache ? 10000 : 15000) :
     error.type === ErrorType.PERMANENT ? 7000 : 10000);

  // Entitlement denial (issue #174): show an upgrade CTA, never a retry.
  if (error.type === ErrorType.ENTITLEMENT) {
    toast.error(error.message, {
      description: error.details || 'Your plan does not include this feature.',
      duration: defaultDuration,
      action: {
        label: 'Upgrade',
        onClick: () => {
          navigateTo('/dashboard/settings?tab=billing');
        },
      },
      onDismiss,
    });
    return;
  }

  // AI Service error with special handling
  if (error.type === ErrorType.AI_SERVICE) {
    if (isFromCache) {
      // Using cached content - show success with warning
      toast.warning(error.message, {
        description: error.details || 'AI service temporarily unavailable. Showing cached content.',
        duration: defaultDuration,
        icon: <HugeiconsIcon icon={Database01Icon} size={20} />,
        action: onRetry && {
          label: 'Generate Fresh',
          onClick: onRetry,
        },
        onDismiss,
      });
    } else if (retryAfter && retryAfter > 0) {
      // Rate limited - show countdown
      // Ensure toast stays visible for entire countdown by using max of retryAfter and default duration
      const countdownDuration = Math.max(retryAfter * 1000, defaultDuration);
      toast.error(error.message, {
        description: (
          <div className="space-y-2">
            <p>{error.details || 'Please wait before retrying'}</p>
            {onRetry && <RetryCountdown initialSeconds={retryAfter} onRetry={onRetry} />}
          </div>
        ),
        duration: countdownDuration,
        onDismiss,
      });
    } else {
      // Generic AI service error
      toast.error(error.message, {
        description: error.details || 'AI service error occurred',
        duration: defaultDuration,
        action: onRetry && error.retryable && {
          label: 'Retry',
          onClick: onRetry,
        },
        onDismiss,
      });
    }
  } else if (error.type === ErrorType.TRANSIENT && error.retryable && onRetry) {
    // Transient error with retry button
    toast.error(error.message, {
      description: error.details || 'Please try again',
      duration: defaultDuration,
      action: {
        label: 'Retry',
        onClick: onRetry,
      },
      onDismiss,
    });
  } else if (error.type === ErrorType.PERMANENT) {
    // Permanent error with field guidance
    const description = error.fieldErrors
      ? Object.entries(error.fieldErrors)
          .map(([field, msg]) => `${field}: ${msg}`)
          .join('\n')
      : error.details || error.suggestedActions?.join('\n');

    toast.error(error.message, {
      description,
      duration: defaultDuration,
      onDismiss,
    });
  } else {
    // System error with correlation ID
    toast.error(error.message, {
      description: `Reference ID: ${error.correlationId}\n${error.suggestedActions?.join('\n') || ''}`,
      duration: defaultDuration,
      onDismiss,
    });
  }
}

/**
 * Show a success notification after error recovery
 *
 * @param message - Success message
 * @param attempts - Number of attempts it took to succeed
 */
export function showRecoveryNotification(message: string, attempts: number) {
  if (attempts > 1) {
    toast.success(message, {
      description: `Succeeded after ${attempts} attempts`,
      duration: 3000,
    });
  } else {
    toast.success(message, {
      duration: 2000,
    });
  }
}

/**
 * ErrorNotification component for custom rendering
 * (Alternative to toast-based notifications)
 */
export function ErrorNotification({
  error,
  onRetry,
  onDismiss,
  isFromCache,
  retryAfter,
}: ErrorNotificationProps) {
  // Severity hue. The card, its left stripe and the icon all derive from it, so
  // they cannot drift apart the way they did before #632 — when the card was a
  // `bg-<hue>-900/NN` overlay authored for a dark page and the stripe and icon
  // were `-500`, leaving a 1.85:1 yellow icon on a light surface.
  const hue =
    error.type === ErrorType.SYSTEM
      ? 'red'
      : error.type === ErrorType.AI_SERVICE && isFromCache
      ? 'blue'
      : error.type === ErrorType.PERMANENT
      ? 'orange'
      : 'yellow';

  // Written out rather than interpolated: Tailwind scans source for whole class
  // names, and `bg-${hue}-50` is not one.
  const bgColor = {
    red: 'bg-red-50 dark:bg-red-900/20 border-red-700 dark:border-red-400',
    blue: 'bg-blue-50 dark:bg-blue-900/20 border-blue-700 dark:border-blue-400',
    orange: 'bg-orange-50 dark:bg-orange-900/20 border-orange-700 dark:border-orange-400',
    yellow: 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-700 dark:border-yellow-400',
  }[hue];

  const iconColor = {
    red: 'text-red-700 dark:text-red-400',
    blue: 'text-blue-700 dark:text-blue-400',
    orange: 'text-orange-700 dark:text-orange-400',
    yellow: 'text-yellow-700 dark:text-yellow-400',
  }[hue];

  return (
    <div
      className={`rounded-lg border-l-4 p-4 ${bgColor}`}
      role="alert"
      aria-live="assertive"
    >
      <div className="flex items-start gap-3">
        {error.type === ErrorType.AI_SERVICE && isFromCache ? (
          <HugeiconsIcon icon={Database01Icon} size={20} className={`flex-shrink-0 mt-0.5 ${iconColor}`} />
        ) : (
          <HugeiconsIcon icon={AlertCircleIcon} size={20} className={`flex-shrink-0 mt-0.5 ${iconColor}`} />
        )}

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-semibold text-foreground">{error.message}</h4>
            {isFromCache && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 border border-blue-300 dark:bg-blue-500/20 dark:text-blue-300 dark:border-blue-500/30">
                <HugeiconsIcon icon={Database01Icon} size={12} />
                Cached Content
              </span>
            )}
          </div>

          {error.details && (
            <p className="text-sm text-muted-foreground mb-2">{error.details}</p>
          )}

          {error.fieldErrors && Object.keys(error.fieldErrors).length > 0 && (
            <ul className="text-sm text-muted-foreground space-y-1 mb-2">
              {Object.entries(error.fieldErrors).map(([field, message]) => (
                <li key={field} className="flex items-start">
                  <span className="font-medium mr-2">{field}:</span>
                  <span>{message}</span>
                </li>
              ))}
            </ul>
          )}

          {error.suggestedActions && error.suggestedActions.length > 0 && (
            <div className="text-sm text-muted-foreground mt-2">
              <p className="font-medium mb-1">What you can do:</p>
              <ul className="list-disc list-inside space-y-0.5">
                {error.suggestedActions.map((action, index) => (
                  <li key={index}>{action}</li>
                ))}
              </ul>
            </div>
          )}

          {error.type === ErrorType.SYSTEM && (
            <p className="text-xs text-muted-foreground mt-2">
              Reference ID: {error.correlationId}
            </p>
          )}

          <div className="flex items-center gap-2 mt-3">
            {retryAfter && retryAfter > 0 && onRetry ? (
              <RetryCountdown initialSeconds={retryAfter} onRetry={onRetry} />
            ) : error.retryable && onRetry ? (
              <Button
                size="sm"
                variant="outline"
                onClick={onRetry}
              >
                <HugeiconsIcon icon={RefreshIcon} size={12} className="mr-1" />
                {isFromCache ? 'Generate Fresh' : 'Retry'}
              </Button>
            ) : null}

            {onDismiss && (
              <Button
                size="sm"
                variant="ghost"
                onClick={onDismiss}
              >
                Dismiss
              </Button>
            )}
          </div>
        </div>

        {onDismiss && (
          <button
            onClick={onDismiss}
            className="flex-shrink-0 text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Dismiss"
          >
            <HugeiconsIcon icon={Cancel01Icon} size={16} />
          </button>
        )}
      </div>
    </div>
  );
}
