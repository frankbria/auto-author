'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { HugeiconsIcon } from '@hugeicons/react';
import { Alert02Icon, Clock01Icon, File01Icon } from '@hugeicons/core-free-icons';
import { formatDistanceToNow } from 'date-fns';

export interface RecoveredData {
  bookId: string;
  chapterId: string;
  content: string;
  timestamp: number;
  error?: string;
}

export interface DataRecoveryModalProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  recoveredData: RecoveredData;
  onRestore: (data: RecoveredData) => void;
  onDiscard: () => void;
}

/**
 * Modal component for recovering backed-up chapter content
 * Shows when localStorage backup is detected on page load
 */
export function DataRecoveryModal({
  isOpen,
  onOpenChange,
  recoveredData,
  onRestore,
  onDiscard,
}: DataRecoveryModalProps) {
  const [isProcessing, setIsProcessing] = useState(false);

  const handleRestore = async () => {
    setIsProcessing(true);
    try {
      await onRestore(recoveredData);
      onOpenChange(false);
    } catch (error) {
      console.error('Failed to restore backup:', error);
      // Keep modal open on error
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDiscard = () => {
    onDiscard();
    onOpenChange(false);
  };

  // Extract preview text (first 100 characters of content, strip HTML)
  const contentPreview = recoveredData.content
    .replace(/<[^>]*>/g, '') // Strip HTML tags
    .trim()
    .substring(0, 100);

  // Format timestamp as relative time
  const timeAgo = formatDistanceToNow(recoveredData.timestamp, { addSuffix: true });

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent
        className="sm:max-w-[525px]"
        aria-describedby="recovery-modal-description"
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <HugeiconsIcon icon={Alert02Icon} size={20} className="text-yellow-500" />
            Unsaved Changes Detected
          </DialogTitle>
          <DialogDescription id="recovery-modal-description">
            We found a local backup of your chapter content from a previous session.
            Would you like to restore it?
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Timestamp Info */}
          <div className="flex items-start gap-3 p-3 bg-muted rounded-lg">
            <HugeiconsIcon icon={Clock01Icon} size={16} className="text-muted-foreground mt-0.5" />
            <div className="flex-1 text-sm">
              <p className="font-medium">Last saved locally:</p>
              <p className="text-muted-foreground">{timeAgo}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {new Date(recoveredData.timestamp).toLocaleString()}
              </p>
            </div>
          </div>

          {/* Error Context (if available) */}
          {recoveredData.error && (
            <div className="flex items-start gap-3 p-3 bg-destructive/10 rounded-lg">
              <HugeiconsIcon icon={Alert02Icon} size={16} className="text-destructive mt-0.5" />
              <div className="flex-1 text-sm">
                <p className="font-medium text-destructive">Previous save failed:</p>
                <p className="text-muted-foreground">{recoveredData.error}</p>
              </div>
            </div>
          )}

          {/* Content Preview */}
          <div className="flex items-start gap-3 p-3 bg-muted rounded-lg">
            <HugeiconsIcon icon={File01Icon} size={16} className="text-muted-foreground mt-0.5" />
            <div className="flex-1 text-sm">
              <p className="font-medium mb-2">Content preview:</p>
              <p className="text-muted-foreground italic">
                {contentPreview}
                {recoveredData.content.length > 100 && '...'}
              </p>
              <p className="text-xs text-muted-foreground mt-2">
                Total characters: {recoveredData.content.length}
              </p>
            </div>
          </div>

          {/* Warning */}
          <div className="text-sm text-muted-foreground border-l-4 border-yellow-500 pl-3 py-1">
            <strong>Note:</strong> Restoring this backup will replace the current content
            in the editor. Make sure you want to do this before proceeding.
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={handleDiscard}
            disabled={isProcessing}
          >
            Discard Backup
          </Button>
          <Button
            onClick={handleRestore}
            disabled={isProcessing}
            className="bg-green-600 hover:bg-green-700"
          >
            {isProcessing ? 'Restoring...' : 'Restore Backup'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
