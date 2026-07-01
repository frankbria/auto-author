/**
 * Export-related type definitions
 * These interfaces define the structure for book export functionality
 */

/**
 * Available export formats
 */
export type ExportFormat = 'pdf' | 'docx' | 'epub' | 'markdown';

/**
 * Page size options for PDF export
 */
export type PageSize = 'letter' | 'A4';

/**
 * Per-side page margins, in inches
 */
export interface TemplateMargins {
  top: number;
  bottom: number;
  inside: number;
  outside: number;
}

/**
 * A professional export template (issue #59).
 * Mirrors the backend spec returned by GET /export/templates.
 */
export interface ExportTemplate {
  id: string;
  name: string;
  description: string;
  category?: string;
  best_for?: string;
  page_size: string;
  margins: TemplateMargins;
  font: { family?: string; pdf_font?: string; docx_font: string; size: number };
  line_height: number;
  first_line_indent: number;
  header: { left: string; right: string };
  footer: { center: string };
}

/**
 * User overrides applied on top of a chosen template.
 */
export interface TemplateCustomization {
  font_size?: number;
  line_height?: number;
  margins?: Partial<TemplateMargins>;
}

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
  /** Professional template id (issue #59); omitted means legacy styling */
  templateId?: string;
  /** Template customization overrides (only meaningful with templateId) */
  customization?: TemplateCustomization;
  /** Markdown only: export one file per chapter as a ZIP (issue #61) */
  markdownMultiFile?: boolean;
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
  /** Professional export templates (issue #59) */
  templates?: ExportTemplate[];
}
