/**
 * Book Type Definitions: book, collaborator and tab-state types
 *
 * Re-exported from `@/types/book`.
 *
 * @module types/book-model
 */

import { CollaboratorRole, ChapterStatus } from './book-enums';
import type { TocItem } from './book-toc';

// ============================================================================
// Collaborator Types
// ============================================================================

/**
 * Schema for book collaborators
 * @see backend/app/schemas/book.py:CollaboratorSchema
 */
export interface Collaborator {
  user_id: string;
  role: CollaboratorRole;
  added_at: string;
}

// ============================================================================
// Book Types
// ============================================================================

/**
 * Base book schema with common fields
 * @see backend/app/schemas/book.py:BookBase
 */
export interface BookBase {
  /** Book title (1-100 characters) */
  title: string;

  /** Optional subtitle (max 255 characters) */
  subtitle?: string;

  /** Optional book description (max 5000 characters) */
  description?: string;

  /** Optional genre classification (max 100 characters) */
  genre?: string;

  /** Optional target audience description (max 100 characters) */
  target_audience?: string;

  /** Additional flexible metadata */
  metadata: Record<string, unknown>;
}

/**
 * Request payload for creating a new book
 * @see backend/app/schemas/book.py:BookCreate
 *
 * @example
 * ```typescript
 * const newBook: BookCreate = {
 *   title: "My Awesome Book",
 *   subtitle: "A Journey Through Words",
 *   description: "This book explores the creative writing process",
 *   genre: "Non-fiction",
 *   target_audience: "Writers and aspiring authors",
 *   metadata: { draft_version: "1.0" }
 * };
 * ```
 */
export interface BookCreate extends BookBase {}

/**
 * Request payload for updating an existing book
 * @see backend/app/schemas/book.py:BookUpdate
 *
 * All fields are optional to support partial updates.
 *
 * @example
 * ```typescript
 * const bookUpdate: BookUpdate = {
 *   title: "Updated Book Title",
 *   description: "A revised description",
 *   published: true
 * };
 * ```
 */
export interface BookUpdate {
  title?: string;
  subtitle?: string;
  description?: string;
  genre?: string;
  target_audience?: string;
  metadata?: Record<string, unknown>;
  published?: boolean;
}

/**
 * Complete book data as returned from API
 * @see backend/app/schemas/book.py:BookResponse
 *
 * This is the primary interface for working with books in the frontend.
 *
 * @example
 * ```typescript
 * const book: BookResponse = await bookClient.getBook(bookId);
 * console.log(`Book: ${book.title}, Chapters: ${book.toc_items.length}`);
 * ```
 */
export interface BookResponse extends BookBase {
  /** Unique book identifier */
  id: string;

  /** Timestamp when book was created */
  created_at: string;

  /** Timestamp when book was last updated */
  updated_at: string;

  /** User ID of the book owner (Clerk ID) */
  owner_id: string;

  /** Cover image URL. Written by the cover upload only; not a request field (#797). */
  cover_image_url?: string;

  /** Cover thumbnail URL, written with the cover (#941). */
  cover_thumbnail_url?: string;

  /** Table of contents items (chapters and sections) */
  toc_items: TocItem[];

  /** Whether the book is published */
  published: boolean;

  /** List of collaborators with access to the book */
  collaborators: Collaborator[];
}

/**
 * Detailed book response including owner information
 * @see backend/app/schemas/book.py:BookDetailResponse
 */
export interface BookDetailResponse extends BookResponse {
  /** Owner user information */
  owner?: Record<string, unknown>;
}

/**
 * Legacy type alias for backward compatibility
 * @deprecated Use BookResponse instead
 */
export type BookProject = BookResponse & {
  /** Computed field: number of chapters (from toc_items.length) */
  chapters: number;

  /** Computed field: progress percentage */
  progress: number;

  /** Optional computed field: total word count across all chapters */
  word_count?: number;
};

// ============================================================================
// Tab State Types
// ============================================================================

/**
 * Request schema for saving tab state
 * @see backend/app/schemas/book.py:TabStateRequest
 */
export interface TabStateRequest {
  active_chapter_id: string;
  open_tab_ids: string[]; // Max 20 tabs
  tab_order: string[];
}

/**
 * Response schema for tab state operations
 * @see backend/app/schemas/book.py:TabStateResponse
 */
export interface TabStateResponse {
  active_chapter_id: string;
  open_tab_ids: string[];
  tab_order: string[];
  last_updated: string;
}

/**
 * Schema for bulk chapter status updates
 * @see backend/app/schemas/book.py:BulkStatusUpdate
 */
export interface BulkStatusUpdate {
  chapter_ids: string[];
  status: ChapterStatus;
  update_timestamp?: boolean;
}
