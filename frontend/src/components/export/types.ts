/**
 * Type definitions for export functionality
 */

export type ExportFormat = 'pdf' | 'docx';
export type PageSize = 'letter' | 'a4';

export interface ExportOptions {
  format: ExportFormat;
  includeEmptyChapters: boolean;
  pageSize?: PageSize; // Only for PDF
}
