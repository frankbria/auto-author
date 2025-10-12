'use client';

import { useEffect, useState } from 'react';
import { Loader2, Download, XCircle, CheckCircle2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { ExportStatus } from '@/types/export';

interface ExportProgressModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Current export status */
  status: ExportStatus;
  /** Progress percentage (0-100) */
  progress?: number;
  /** Estimated time remaining in seconds */
  estimatedTime?: number;
  /** Error message if export failed */
  error?: string;
  /** Callback when user cancels export */
  onCancel?: () => void;
  /** Callback when user closes the modal after completion/error */
  onClose: () => void;
  /** Filename of the exported file */
  filename?: string;
}

/**
 * Modal showing export progress with status updates
 *
 * Displays different states:
 * - Pending: Preparing export
 * - Processing: Shows progress bar and estimated time
 * - Completed: Success message with filename
 * - Failed: Error message with option to retry
 *
 * @example
 * ```tsx
 * <ExportProgressModal
 *   isOpen={isExporting}
 *   status={exportStatus}
 *   progress={exportProgress}
 *   estimatedTime={30}
 *   onCancel={handleCancelExport}
 *   onClose={handleCloseProgress}
 * />
 * ```
 */
export function ExportProgressModal({
  isOpen,
  status,
  progress = 0,
  estimatedTime,
  error,
  onCancel,
  onClose,
  filename,
}: ExportProgressModalProps) {
  const [elapsedTime, setElapsedTime] = useState(0);

  // Track elapsed time while processing
  useEffect(() => {
    if (status === 'processing' || status === 'pending') {
      setElapsedTime(0);
      const interval = setInterval(() => {
        setElapsedTime((prev) => prev + 1);
      }, 1000);

      return () => clearInterval(interval);
    }
  }, [status]);

  const formatTime = (seconds: number) => {
    if (seconds < 60) {
      return `${seconds}s`;
    }
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="h-12 w-12 text-green-500" />;
      case 'failed':
        return <XCircle className="h-12 w-12 text-red-500" />;
      case 'processing':
      case 'pending':
      default:
        return <Loader2 className="h-12 w-12 text-primary animate-spin" />;
    }
  };

  const getStatusTitle = () => {
    switch (status) {
      case 'pending':
        return 'Preparing Export...';
      case 'processing':
        return 'Generating Export...';
      case 'completed':
        return 'Export Complete!';
      case 'failed':
        return 'Export Failed';
      default:
        return 'Exporting...';
    }
  };

  const getStatusDescription = () => {
    switch (status) {
      case 'pending':
        return 'Preparing your book for export';
      case 'processing':
        return 'Converting your content to the selected format';
      case 'completed':
        return filename
          ? `Your book has been exported successfully as ${filename}`
          : 'Your book has been exported successfully';
      case 'failed':
        return error || 'An error occurred while exporting your book. Please try again.';
      default:
        return 'Processing...';
    }
  };

  const canCancel = status === 'pending' || status === 'processing';
  const isComplete = status === 'completed' || status === 'failed';

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className="sm:max-w-[450px] bg-background border-input"
        onPointerDownOutside={(e) => canCancel ? undefined : e.preventDefault()}
        onEscapeKeyDown={(e) => canCancel ? undefined : e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            {getStatusIcon()}
            <span>{getStatusTitle()}</span>
          </DialogTitle>
          <DialogDescription>
            {getStatusDescription()}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Progress Bar for Processing State */}
          {(status === 'processing' || status === 'pending') && (
            <div className="space-y-2">
              <Progress value={progress} className="h-2" />
              <div className="flex justify-between text-sm text-muted-foreground">
                <span>{progress}% complete</span>
                {estimatedTime !== undefined && (
                  <span>
                    ~{formatTime(estimatedTime)} remaining
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Elapsed Time for Long Operations */}
          {(status === 'processing' || status === 'pending') && elapsedTime > 10 && (
            <div className="text-sm text-muted-foreground text-center">
              {elapsedTime > 20 ? (
                <>This is taking longer than expected. Large books may take up to a minute.</>
              ) : (
                <>Elapsed time: {formatTime(elapsedTime)}</>
              )}
            </div>
          )}

          {/* Success Actions */}
          {status === 'completed' && (
            <div className="flex justify-center pt-2">
              <Button onClick={onClose} className="min-w-[120px]">
                <Download className="h-4 w-4 mr-2" />
                Done
              </Button>
            </div>
          )}

          {/* Error Actions */}
          {status === 'failed' && (
            <div className="flex justify-center gap-2 pt-2">
              <Button variant="outline" onClick={onClose}>
                Close
              </Button>
              {onCancel && (
                <Button onClick={onCancel}>
                  Retry Export
                </Button>
              )}
            </div>
          )}

          {/* Cancel Button for In-Progress */}
          {canCancel && onCancel && (
            <div className="flex justify-center pt-2">
              <Button variant="outline" onClick={onCancel}>
                Cancel Export
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
