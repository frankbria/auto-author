'use client';

import { useState, useEffect } from 'react';
import { HugeiconsIcon } from '@hugeicons/react';
import { Download01Icon, File01Icon, Cancel01Icon } from '@hugeicons/core-free-icons';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Switch } from '@/components/ui/switch';
import { ExportOptions, ExportFormat, PageSize, BookExportStats } from '@/types/export';
import { usePerformanceTracking } from '@/hooks/usePerformanceTracking';
import bookClient from '@/lib/api/bookClient';

interface ExportOptionsModalProps {
  /** Book ID to export */
  bookId: string;
  /** Whether the modal is open */
  isOpen: boolean;
  /** Callback when modal open state changes */
  onOpenChange: (open: boolean) => void;
  /** Callback when export is initiated with options */
  onExport: (options: ExportOptions) => void;
  /** Book title for display */
  bookTitle?: string;
}

/**
 * Modal for configuring book export options
 *
 * Allows users to select:
 * - Export format (PDF or DOCX)
 * - Page size for PDF (Letter or A4)
 * - Whether to include empty chapters
 * - Specific chapters to export (future feature)
 *
 * @example
 * ```tsx
 * <ExportOptionsModal
 *   bookId="book-123"
 *   isOpen={showExportModal}
 *   onOpenChange={setShowExportModal}
 *   onExport={handleExport}
 *   bookTitle="My Book"
 * />
 * ```
 */
export function ExportOptionsModal({
  bookId,
  isOpen,
  onOpenChange,
  onExport,
  bookTitle,
}: ExportOptionsModalProps) {
  const { trackOperation } = usePerformanceTracking();

  // Export options state
  const [format, setFormat] = useState<ExportFormat>('pdf');
  const [pageSize, setPageSize] = useState<PageSize>('letter');
  const [includeEmptyChapters, setIncludeEmptyChapters] = useState(false);

  // Book statistics
  const [stats, setStats] = useState<BookExportStats | null>(null);
  const [loadingStats, setLoadingStats] = useState(false);

  // Load book statistics when modal opens
  useEffect(() => {
    if (isOpen && bookId) {
      loadBookStats();
    }
  }, [isOpen, bookId]);

  const loadBookStats = async () => {
    try {
      setLoadingStats(true);
      const { data: response } = await trackOperation('export-stats', async () => {
        return await bookClient.getExportFormats(bookId);
      }, { bookId });
      setStats(response.book_stats);
    } catch (error) {
      console.error('Failed to load book statistics:', error);
      toast.error('Failed to load book information');
    } finally {
      setLoadingStats(false);
    }
  };

  const handleExport = () => {
    const options: ExportOptions = {
      format,
      includeEmptyChapters,
      pageSize: format === 'pdf' ? pageSize : undefined,
    };

    onExport(options);
  };

  const getEstimatedSize = () => {
    if (!stats) return 'Calculating...';

    // Rough estimate: 1 page ≈ 500 words ≈ 50KB for PDF, 20KB for DOCX
    const pages = stats.estimated_pages || Math.ceil(stats.total_word_count / 500);
    const sizeKB = format === 'pdf' ? pages * 50 : pages * 20;

    if (sizeKB < 1024) {
      return `~${Math.round(sizeKB)} KB`;
    } else {
      return `~${(sizeKB / 1024).toFixed(1)} MB`;
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px] bg-background border-input">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <HugeiconsIcon icon={Download01Icon} size={20} />
            Export Book
          </DialogTitle>
          <DialogDescription>
            {bookTitle && (
              <span className="font-medium text-foreground">
                {bookTitle}
              </span>
            )}
            {bookTitle && ' · '}
            Configure export options for your book
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Book Statistics */}
          {stats && !loadingStats && (
            <div className="rounded-lg bg-muted p-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Total Chapters:</span>
                <span className="font-medium">{stats.total_chapters}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Chapters with Content:</span>
                <span className="font-medium">{stats.chapters_with_content}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Total Words:</span>
                <span className="font-medium">{stats.total_word_count.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Estimated Pages:</span>
                <span className="font-medium">{stats.estimated_pages}</span>
              </div>
            </div>
          )}

          {/* Format Selection */}
          <div className="space-y-3">
            <Label className="text-base font-semibold">Export Format</Label>
            <RadioGroup value={format} onValueChange={(value) => setFormat(value as ExportFormat)}>
              <div className="flex items-start space-x-3 space-y-0 rounded-md border p-4 hover:bg-accent">
                <RadioGroupItem value="pdf" id="format-pdf" />
                <div className="flex-1">
                  <Label
                    htmlFor="format-pdf"
                    className="font-medium cursor-pointer"
                  >
                    PDF Document
                  </Label>
                  <p className="text-sm text-muted-foreground mt-1">
                    Portable Document Format - ideal for printing and sharing. Preserves formatting.
                  </p>
                </div>
                <HugeiconsIcon icon={File01Icon} size={20} className="text-red-500" />
              </div>

              <div className="flex items-start space-x-3 space-y-0 rounded-md border p-4 hover:bg-accent">
                <RadioGroupItem value="docx" id="format-docx" />
                <div className="flex-1">
                  <Label
                    htmlFor="format-docx"
                    className="font-medium cursor-pointer"
                  >
                    Word Document
                  </Label>
                  <p className="text-sm text-muted-foreground mt-1">
                    Microsoft Word format - editable and compatible with most word processors.
                  </p>
                </div>
                <HugeiconsIcon icon={File01Icon} size={20} className="text-blue-500" />
              </div>
            </RadioGroup>
          </div>

          {/* Page Size (PDF only) */}
          {format === 'pdf' && (
            <div className="space-y-3">
              <Label className="text-base font-semibold">Page Size</Label>
              <RadioGroup value={pageSize} onValueChange={(value) => setPageSize(value as PageSize)}>
                <div className="flex items-center space-x-3 space-y-0">
                  <RadioGroupItem value="letter" id="size-letter" />
                  <Label htmlFor="size-letter" className="font-normal cursor-pointer">
                    Letter (8.5" × 11") - US Standard
                  </Label>
                </div>
                <div className="flex items-center space-x-3 space-y-0">
                  <RadioGroupItem value="A4" id="size-a4" />
                  <Label htmlFor="size-a4" className="font-normal cursor-pointer">
                    A4 (210mm × 297mm) - International Standard
                  </Label>
                </div>
              </RadioGroup>
            </div>
          )}

          {/* Include Empty Chapters */}
          <div className="flex items-center justify-between space-x-2 rounded-lg border p-4">
            <div className="space-y-0.5 flex-1">
              <Label htmlFor="include-empty" className="text-base cursor-pointer">
                Include Empty Chapters
              </Label>
              <p className="text-sm text-muted-foreground">
                Include chapters that don't have any content yet
                {stats && stats.total_chapters > stats.chapters_with_content && (
                  <span className="ml-1">
                    ({stats.total_chapters - stats.chapters_with_content} empty)
                  </span>
                )}
              </p>
            </div>
            <Switch
              id="include-empty"
              checked={includeEmptyChapters}
              onCheckedChange={setIncludeEmptyChapters}
            />
          </div>

          {/* Estimated File Size */}
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Estimated file size:</span>
            <span className="font-medium">{getEstimatedSize()}</span>
          </div>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            <HugeiconsIcon icon={Cancel01Icon} size={16} className="mr-2" />
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleExport}
            disabled={loadingStats}
          >
            <HugeiconsIcon icon={Download01Icon} size={16} className="mr-2" />
            Export {format.toUpperCase()}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
