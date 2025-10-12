'use client';

import { toast } from 'sonner';
import { ClassifiedError, ErrorType } from '@/lib/errors';
import { AlertCircle, RefreshCw, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

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
  } = {}
) {
  const { onRetry, onDismiss, duration } = options;

  // Determine default duration based on error type
  const defaultDuration =
    duration ||
    (error.type === ErrorType.TRANSIENT ? 5000 : error.type === ErrorType.PERMANENT ? 7000 : 10000);

  // Create notification content based on error type
  if (error.type === ErrorType.TRANSIENT && error.retryable && onRetry) {
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
      description: `Succeeded after ${attempts} ${attempts === 2 ? 'attempt' : 'attempts'}`,
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
}: ErrorNotificationProps) {
  const bgColor =
    error.type === ErrorType.SYSTEM
      ? 'bg-red-900/20 border-red-500'
      : error.type === ErrorType.PERMANENT
      ? 'bg-orange-900/20 border-orange-500'
      : 'bg-yellow-900/20 border-yellow-500';

  const iconColor =
    error.type === ErrorType.SYSTEM
      ? 'text-red-500'
      : error.type === ErrorType.PERMANENT
      ? 'text-orange-500'
      : 'text-yellow-500';

  return (
    <div
      className={`rounded-lg border-l-4 p-4 ${bgColor}`}
      role="alert"
      aria-live="assertive"
    >
      <div className="flex items-start gap-3">
        <AlertCircle className={`h-5 w-5 flex-shrink-0 mt-0.5 ${iconColor}`} />

        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-white mb-1">{error.message}</h4>

          {error.details && (
            <p className="text-sm text-zinc-300 mb-2">{error.details}</p>
          )}

          {error.fieldErrors && Object.keys(error.fieldErrors).length > 0 && (
            <ul className="text-sm text-zinc-300 space-y-1 mb-2">
              {Object.entries(error.fieldErrors).map(([field, message]) => (
                <li key={field} className="flex items-start">
                  <span className="font-medium mr-2">{field}:</span>
                  <span>{message}</span>
                </li>
              ))}
            </ul>
          )}

          {error.suggestedActions && error.suggestedActions.length > 0 && (
            <div className="text-sm text-zinc-400 mt-2">
              <p className="font-medium mb-1">What you can do:</p>
              <ul className="list-disc list-inside space-y-0.5">
                {error.suggestedActions.map((action, index) => (
                  <li key={index}>{action}</li>
                ))}
              </ul>
            </div>
          )}

          {error.type === ErrorType.SYSTEM && (
            <p className="text-xs text-zinc-500 mt-2">
              Reference ID: {error.correlationId}
            </p>
          )}

          <div className="flex items-center gap-2 mt-3">
            {error.retryable && onRetry && (
              <Button
                size="sm"
                variant="outline"
                onClick={onRetry}
                className="text-white border-white/20 hover:bg-white/10"
              >
                <RefreshCw className="h-3 w-3 mr-1" />
                Retry
              </Button>
            )}

            {onDismiss && (
              <Button
                size="sm"
                variant="ghost"
                onClick={onDismiss}
                className="text-zinc-400 hover:text-white"
              >
                Dismiss
              </Button>
            )}
          </div>
        </div>

        {onDismiss && (
          <button
            onClick={onDismiss}
            className="flex-shrink-0 text-zinc-400 hover:text-white transition-colors"
            aria-label="Dismiss"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}
