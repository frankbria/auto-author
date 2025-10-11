/**
 * Export-related type definitions
 * These interfaces define the structure for book export functionality
 */

/**
 * Available export formats
 */
export type ExportFormat = 'pdf' | 'docx';

/**
 * Page size options for PDF export
 */
export type PageSize = 'letter' | 'a4';

/**
 * Export options provided by user
 */
export interface ExportOptions {
  /** Export format (PDF or DOCX) */
  format: ExportFormat;
  /** Include chapters with no content */
  includeEmptyChapters: boolean;
  /** Page size for PDF export (ignored for DOCX) */
  pageSize?: PageSize;
  /** Optional: specific chapter IDs to export (if not provided, exports all) */
  chapters?: string[];
}

/**
 * Export response metadata
 */
export interface ExportResponse {
  /** Download URL for the generated file */
  downloadUrl: string;
  /** Generated filename */
  filename: string;
  /** File size in bytes */
  fileSize: number;
  /** Expiration timestamp for download URL (ISO 8601) */
  expiresAt: string;
}

/**
 * Export error types
 */
export type ExportErrorCode =
  | 'TIMEOUT'
  | 'SIZE_LIMIT'
  | 'GENERATION_FAILED'
  | 'NETWORK_ERROR'
  | 'UNAUTHORIZED'
  | 'NOT_FOUND';

/**
 * Export error information
 */
export interface ExportError {
  /** Error code for programmatic handling */
  code: ExportErrorCode;
  /** Human-readable error message */
  message: string;
  /** Whether the operation can be retried */
  retryable: boolean;
  /** HTTP status code */
  statusCode?: number;
}

/**
 * Export progress status
 */
export type ExportStatus = 'pending' | 'processing' | 'completed' | 'failed';

/**
 * Export progress information
 */
export interface ExportProgressInfo {
  /** Current status */
  status: ExportStatus;
  /** Progress percentage (0-100) */
  progress: number;
  /** Estimated time remaining in seconds */
  estimatedTimeRemaining?: number;
  /** Error information if status is 'failed' */
  error?: ExportError;
}

/**
 * Format metadata from backend
 */
export interface ExportFormatInfo {
  format: string;
  name: string;
  description: string;
  mime_type: string;
  extension: string;
  available: boolean;
  options?: Record<string, unknown>;
}

/**
 * Book statistics for export
 */
export interface BookExportStats {
  total_chapters: number;
  chapters_with_content: number;
  total_word_count: number;
  estimated_pages: number;
}

/**
 * Available formats response from backend
 */
export interface ExportFormatsResponse {
  formats: ExportFormatInfo[];
  book_stats: BookExportStats;
}
