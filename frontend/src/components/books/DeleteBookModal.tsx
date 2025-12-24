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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { HugeiconsIcon } from '@hugeicons/react';
import { Alert02Icon, Loading03Icon } from '@hugeicons/core-free-icons';

/**
 * Delete book modal props
 */
export interface DeleteBookModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Callback when modal open state changes */
  onOpenChange: (open: boolean) => void;
  /** Book title to delete */
  bookTitle: string;
  /** Book statistics for display */
  bookStats?: {
    chapterCount: number;
    wordCount: number;
  };
  /** Callback when user confirms deletion */
  onConfirm: () => void | Promise<void>;
  /** Whether deletion is in progress */
  isDeleting?: boolean;
}

/**
 * Confirmation modal for book deletion
 *
 * Requires user to type exact book title to prevent accidental deletion.
 * Displays book statistics and data loss warning.
 *
 * @example
 * ```tsx
 * <DeleteBookModal
 *   isOpen={showDeleteModal}
 *   onOpenChange={setShowDeleteModal}
 *   bookTitle="My Novel"
 *   bookStats={{ chapterCount: 12, wordCount: 50000 }}
 *   onConfirm={handleDeleteBook}
 *   isDeleting={isDeleting}
 * />
 * ```
 */
export function DeleteBookModal({
  isOpen,
  onOpenChange,
  bookTitle,
  bookStats,
  onConfirm,
  isDeleting = false,
}: DeleteBookModalProps) {
  const [confirmationText, setConfirmationText] = useState('');

  // Check if user typed exact book title
  const isConfirmed = confirmationText === bookTitle;

  const handleConfirm = async () => {
    if (!isConfirmed || isDeleting) return;

    await onConfirm();

    // Reset confirmation text on close
    setConfirmationText('');
  };

  const handleCancel = () => {
    if (isDeleting) return; // Prevent closing during deletion

    setConfirmationText('');
    onOpenChange(false);
  };

  // Reset confirmation when modal closes
  const handleOpenChange = (open: boolean) => {
    if (!open && !isDeleting) {
      setConfirmationText('');
    }
    onOpenChange(open);
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent
        className="sm:max-w-[500px] bg-background border-destructive/50 transition-all"
        onPointerDownOutside={(e) => isDeleting && e.preventDefault()}
        onEscapeKeyDown={(e) => isDeleting && e.preventDefault()}
        data-slot="delete-modal"
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-destructive transition-all">
            <HugeiconsIcon icon={Alert02Icon} size={20} />
            Delete Book Permanently?
          </DialogTitle>
          <DialogDescription className="text-base transition-all">
            This action cannot be undone. This will permanently delete the book and all
            its content from your account.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4 transition-all">
          {/* Book Information */}
          <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4 space-y-2 transition-all">
            <div className="font-semibold text-foreground">{bookTitle}</div>
            {bookStats && (
              <div className="text-sm text-muted-foreground space-y-1">
                <div>Chapters: {bookStats.chapterCount}</div>
                <div>Words: {bookStats.wordCount.toLocaleString()}</div>
              </div>
            )}
          </div>

          {/* Data Loss Warning */}
          <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 p-4 transition-all">
            <div className="flex items-start gap-2">
              <HugeiconsIcon icon={Alert02Icon} size={16} color="rgb(234 179 8)" className="mt-0.5 flex-shrink-0" />
              <div className="text-sm text-foreground">
                <p className="font-medium mb-1">All data will be permanently deleted:</p>
                <ul className="list-disc list-inside space-y-0.5 text-muted-foreground">
                  <li>All chapters and subchapters</li>
                  <li>All chapter content and drafts</li>
                  <li>Table of contents</li>
                  <li>Book metadata and settings</li>
                  <li>Questions and responses</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Confirmation Input */}
          <div className="space-y-2 transition-all">
            <Label htmlFor="confirm-delete" className="text-foreground transition-all">
              Type <span className="font-mono font-bold">{bookTitle}</span> to confirm
            </Label>
            <Input
              id="confirm-delete"
              type="text"
              value={confirmationText}
              onChange={(e) => setConfirmationText(e.target.value)}
              placeholder="Enter book title exactly"
              disabled={isDeleting}
              className="font-mono transition-all focus-visible:ring-[3px]"
              autoComplete="off"
              autoFocus
            />
            {confirmationText && !isConfirmed && (
              <p className="text-xs text-destructive transition-all">
                Title must match exactly (case-sensitive)
              </p>
            )}
          </div>
        </div>

        <DialogFooter className="transition-all">
          <Button
            variant="outline"
            onClick={handleCancel}
            disabled={isDeleting}
            className="transition-all focus-visible:ring-[3px]"
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleConfirm}
            disabled={!isConfirmed || isDeleting}
            className="transition-all focus-visible:ring-[3px]"
          >
            {isDeleting ? (
              <>
                <HugeiconsIcon icon={Loading03Icon} size={16} className="mr-2 animate-spin" />
                Deleting...
              </>
            ) : (
              'Delete Permanently'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
