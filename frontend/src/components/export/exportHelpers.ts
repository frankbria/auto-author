/**
 * Export helper utilities
 * Functions for handling file downloads and export operations
 */

import { ExportFormat } from '@/types/export';

/**
 * Download a blob as a file
 *
 * Creates a temporary download link and triggers download
 *
 * @param blob - The file blob to download
 * @param filename - The filename to save as
 *
 * @example
 * ```ts
 * const pdfBlob = await bookClient.exportPDF(bookId);
 * downloadBlob(pdfBlob, 'my-book.pdf');
 * ```
 */
export function downloadBlob(blob: Blob, filename: string): void {
  // Create object URL for the blob
  const url = window.URL.createObjectURL(blob);

  // Create temporary link element
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.style.display = 'none';

  // Append to document, click, and cleanup
  document.body.appendChild(link);
  link.click();

  // Cleanup
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

/**
 * Generate filename for export
 *
 * Creates a sanitized filename from book title and format
 *
 * @param bookTitle - The book title
 * @param format - Export format (pdf or docx)
 * @returns Sanitized filename with extension
 *
 * @example
 * ```ts
 * const filename = generateFilename('My Book: A Story', 'pdf');
 * // Returns: 'my-book-a-story.pdf'
 * ```
 */
export function generateFilename(bookTitle: string, format: ExportFormat): string {
  // Sanitize title: lowercase, replace spaces/special chars with hyphens
  const sanitized = bookTitle
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, ''); // Remove leading/trailing hyphens

  // Add extension
  return `${sanitized}.${format}`;
}

/**
 * Format file size in human-readable format
 *
 * @param bytes - File size in bytes
 * @returns Formatted size string (e.g., "2.3 MB")
 *
 * @example
 * ```ts
 * formatFileSize(1024); // "1.0 KB"
 * formatFileSize(2500000); // "2.4 MB"
 * ```
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB'];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${units[i]}`;
}

/**
 * Validate export options
 *
 * Checks if export options are valid before initiating export
 *
 * @param format - Export format
 * @param bookTitle - Book title (optional, for filename validation)
 * @returns Object with isValid flag and error message if invalid
 *
 * @example
 * ```ts
 * const validation = validateExportOptions('pdf', 'My Book');
 * if (!validation.isValid) {
 *   console.error(validation.error);
 * }
 * ```
 */
export function validateExportOptions(
  format: ExportFormat,
  bookTitle?: string
): { isValid: boolean; error?: string } {
  // Check format
  if (!['pdf', 'docx'].includes(format)) {
    return {
      isValid: false,
      error: 'Invalid export format. Must be "pdf" or "docx".',
    };
  }

  // Check book title if provided
  if (bookTitle && bookTitle.trim().length === 0) {
    return {
      isValid: false,
      error: 'Book title cannot be empty.',
    };
  }

  return { isValid: true };
}

/**
 * Estimate export time based on content size
 *
 * Provides rough estimate for progress display
 *
 * @param wordCount - Total word count of book
 * @param format - Export format
 * @returns Estimated time in seconds
 *
 * @example
 * ```ts
 * const estimate = estimateExportTime(50000, 'pdf');
 * // Returns: ~15 seconds
 * ```
 */
export function estimateExportTime(wordCount: number, format: ExportFormat): number {
  // Base estimates (seconds per 1000 words):
  // PDF: ~0.5s per 1000 words (slower due to formatting)
  // DOCX: ~0.3s per 1000 words (faster, simpler format)
  const ratePerThousand = format === 'pdf' ? 0.5 : 0.3;

  // Calculate estimate with minimum of 2 seconds
  const estimate = Math.max(2, Math.ceil((wordCount / 1000) * ratePerThousand));

  return estimate;
}
