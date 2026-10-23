/**
 * Book Type Definitions: table of contents (chapter) types
 *
 * Re-exported from `@/types/book`.
 *
 * @module types/book-toc
 */

import { ChapterStatus } from './book-enums';

// ============================================================================
// Table of Contents (Chapter) Types
// ============================================================================

/**
 * Table of Contents item representing a chapter or section
 * @see backend/app/schemas/book.py:TocItemSchema
 */
export interface TocItem {
  /** Unique identifier for the TOC item */
  id: string;

  /** Title of the chapter/section */
  title: string;

  /** Hierarchical level (1 = chapter, 2 = section, etc.) */
  level: number;

  /** Optional description of the chapter content */
  description?: string;

  /** ID of parent item (for nested sections) */
  parent_id?: string;

  /** Position in the table of contents */
  order: number;

  /** Reference to content collection if needed */
  content_id?: string;

  /** Current status of the chapter */
  status: ChapterStatus;

  /** Word count for this chapter */
  word_count: number;

  /** Last modification timestamp */
  last_modified?: string;

  /** Estimated reading time in minutes */
  estimated_reading_time: number;

  /** Whether this tab is currently active (for tab persistence) */
  is_active_tab: boolean;

  /** Additional metadata */
  metadata: Record<string, unknown>;
}

/**
 * Request payload for creating a new TOC item
 * @see backend/app/schemas/book.py:TocItemCreate
 */
export interface TocItemCreate {
  title: string;
  level?: number;
  description?: string;
  parent_id?: string;
  order: number;
  metadata?: Record<string, unknown>;
}

/**
 * Request payload for updating a TOC item
 * @see backend/app/schemas/book.py:TocItemUpdate
 */
export interface TocItemUpdate {
  title?: string;
  description?: string;
  parent_id?: string;
  order?: number;
  level?: number;
  metadata?: Record<string, unknown>;
}

/**
 * Enhanced chapter metadata for tab functionality
 * @see backend/app/schemas/book.py:ChapterMetadata
 */
export interface ChapterMetadata {
  id: string;
  title: string;
  status: ChapterStatus;
  word_count: number;
  last_modified?: string;
  estimated_reading_time: number;
  order: number;
  level: number;
  has_content: boolean;
  description?: string;
  parent_id?: string;
}

/**
 * Response schema for chapter metadata operations
 * @see backend/app/schemas/book.py:ChapterMetadataResponse
 */
export interface ChapterMetadataResponse {
  book_id: string;
  chapters: ChapterMetadata[];
  total_chapters: number;
  completion_stats: Record<string, number>;
  last_active_chapter?: string;
}
