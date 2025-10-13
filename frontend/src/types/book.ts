/**
 * Book Type Definitions
 *
 * Complete type definitions for the Auto-Author book management system.
 * These types align with the backend Pydantic schemas and database models.
 *
 * @module types/book
 * @see backend/app/schemas/book.py - Backend schema definitions
 * @see backend/app/models/book.py - Backend database models
 */

import { ApiResponse } from './api';

// ============================================================================
// Enums
// ============================================================================

/**
 * Valid status values for chapters/TOC items
 * @see backend/app/schemas/book.py:ChapterStatus
 */
export enum ChapterStatus {
  DRAFT = 'draft',
  IN_PROGRESS = 'in-progress',
  COMPLETED = 'completed',
  PUBLISHED = 'published',
}

/**
 * Types of questions that can be generated for a chapter
 * @see backend/app/schemas/book.py:QuestionType
 */
export enum QuestionType {
  CHARACTER = 'character',
  PLOT = 'plot',
  SETTING = 'setting',
  THEME = 'theme',
  RESEARCH = 'research',
}

/**
 * Difficulty levels for questions
 * @see backend/app/schemas/book.py:QuestionDifficulty
 */
export enum QuestionDifficulty {
  EASY = 'easy',
  MEDIUM = 'medium',
  HARD = 'hard',
}

/**
 * Status values for question responses
 * @see backend/app/schemas/book.py:ResponseStatus
 */
export enum ResponseStatus {
  DRAFT = 'draft',
  COMPLETED = 'completed',
}

/**
 * Roles for book collaborators
 */
export enum CollaboratorRole {
  VIEWER = 'viewer',
  EDITOR = 'editor',
  CO_AUTHOR = 'co-author',
}

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

// ============================================================================
// Question Types
// ============================================================================

/**
 * Metadata for questions
 * @see backend/app/schemas/book.py:QuestionMetadata
 */
export interface QuestionMetadata {
  suggested_response_length: string;
  help_text?: string;
  examples?: string[];
}

/**
 * Base schema for chapter questions
 * @see backend/app/schemas/book.py:QuestionBase
 */
export interface QuestionBase {
  question_text: string;
  question_type: QuestionType;
  difficulty: QuestionDifficulty;
  category: string;
  order: number;
  metadata: QuestionMetadata;
}

/**
 * Complete question with all fields
 * @see backend/app/schemas/book.py:Question
 */
export interface Question extends QuestionBase {
  id: string;
  book_id: string;
  chapter_id: string;
  generated_at: string;
}

/**
 * Request payload for creating a new question
 * @see backend/app/schemas/book.py:QuestionCreate
 */
export interface QuestionCreate extends QuestionBase {
  book_id: string;
  chapter_id: string;
}

/**
 * Metadata for question responses including edit history
 * @see backend/app/schemas/book.py:QuestionResponseMetadata
 */
export interface QuestionResponseMetadata {
  edit_history: Array<{
    timestamp: string;
    word_count: number;
  }>;
}

/**
 * Base schema for question responses
 * @see backend/app/schemas/book.py:QuestionResponseBase
 */
export interface QuestionResponseBase {
  response_text: string;
  word_count: number;
  status: ResponseStatus;
}

/**
 * Complete question response with all fields
 * @see backend/app/schemas/book.py:QuestionResponse
 */
export interface QuestionResponse extends QuestionResponseBase {
  id: string;
  question_id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  last_edited_at: string;
  metadata: QuestionResponseMetadata;
}

/**
 * Request payload for creating a question response
 * @see backend/app/schemas/book.py:QuestionResponseCreate
 */
export interface QuestionResponseCreate extends QuestionResponseBase {
  question_id: string;
}

/**
 * Schema for rating a question's relevance/quality
 * @see backend/app/schemas/book.py:QuestionRating
 */
export interface QuestionRating {
  question_id: string;
  user_id: string;
  rating: number; // 1-5
  feedback?: string;
  created_at: string;
}

// ============================================================================
// Question API Request/Response Types
// ============================================================================

/**
 * Request schema for generating questions for a chapter
 * @see backend/app/schemas/book.py:GenerateQuestionsRequest
 */
export interface GenerateQuestionsRequest {
  count?: number; // 1-50, default 10
  difficulty?: QuestionDifficulty;
  focus?: QuestionType[];
}

/**
 * Response schema for generated questions
 * @see backend/app/schemas/book.py:GenerateQuestionsResponse
 */
export interface GenerateQuestionsResponse {
  questions: Question[];
  generation_id: string;
  total: number;
}

/**
 * Query parameters for listing questions
 * @see backend/app/schemas/book.py:QuestionListParams
 */
export interface QuestionListParams {
  status?: string;
  category?: string;
  question_type?: QuestionType;
  page?: number;
  limit?: number;
}

/**
 * Response schema for listing questions
 * @see backend/app/schemas/book.py:QuestionListResponse
 */
export interface QuestionListResponse {
  questions: Question[];
  total: number;
  page: number;
  pages: number;
}

/**
 * Response schema for chapter question progress
 * @see backend/app/schemas/book.py:QuestionProgressResponse
 */
export interface QuestionProgressResponse {
  total: number;
  completed: number;
  progress: number; // 0.0 to 1.0
  status: string; // "not-started", "in-progress", "completed"
}

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

  /** Optional URL to book cover image (max 2083 characters) */
  cover_image_url?: string;

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
 *   cover_image_url: "https://example.com/cover.jpg",
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
  cover_image_url?: string;
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

// ============================================================================
// Type Guards and Validation Utilities
// ============================================================================

/**
 * Type guard to check if a value is a valid ChapterStatus
 *
 * @param value - Value to check
 * @returns True if value is a valid ChapterStatus
 *
 * @example
 * ```typescript
 * if (isChapterStatus(status)) {
 *   chapter.status = status;
 * }
 * ```
 */
export function isChapterStatus(value: unknown): value is ChapterStatus {
  return (
    typeof value === 'string' &&
    Object.values(ChapterStatus).includes(value as ChapterStatus)
  );
}

/**
 * Type guard to check if a value is a valid QuestionType
 *
 * @param value - Value to check
 * @returns True if value is a valid QuestionType
 */
export function isQuestionType(value: unknown): value is QuestionType {
  return (
    typeof value === 'string' &&
    Object.values(QuestionType).includes(value as QuestionType)
  );
}

/**
 * Type guard to check if a value is a valid QuestionDifficulty
 *
 * @param value - Value to check
 * @returns True if value is a valid QuestionDifficulty
 */
export function isQuestionDifficulty(value: unknown): value is QuestionDifficulty {
  return (
    typeof value === 'string' &&
    Object.values(QuestionDifficulty).includes(value as QuestionDifficulty)
  );
}

/**
 * Type guard to check if an object is a valid TocItem
 *
 * @param obj - Object to check
 * @returns True if object is a valid TocItem
 *
 * @example
 * ```typescript
 * if (isTocItem(data)) {
 *   console.log(`Chapter: ${data.title}, Status: ${data.status}`);
 * }
 * ```
 */
export function isTocItem(obj: unknown): obj is TocItem {
  if (typeof obj !== 'object' || obj === null) return false;

  const item = obj as Record<string, unknown>;

  return (
    typeof item.id === 'string' &&
    typeof item.title === 'string' &&
    typeof item.level === 'number' &&
    typeof item.order === 'number' &&
    isChapterStatus(item.status) &&
    typeof item.word_count === 'number' &&
    typeof item.estimated_reading_time === 'number' &&
    typeof item.is_active_tab === 'boolean' &&
    typeof item.metadata === 'object' &&
    item.metadata !== null
  );
}

/**
 * Type guard to check if an object is a valid BookResponse
 *
 * @param obj - Object to check
 * @returns True if object is a valid BookResponse
 *
 * @example
 * ```typescript
 * const data = await fetch('/api/books/123').then(r => r.json());
 * if (isBookResponse(data)) {
 *   // TypeScript now knows data is BookResponse
 *   console.log(data.title);
 * }
 * ```
 */
export function isBookResponse(obj: unknown): obj is BookResponse {
  if (typeof obj !== 'object' || obj === null) return false;

  const book = obj as Record<string, unknown>;

  return (
    typeof book.id === 'string' &&
    typeof book.title === 'string' &&
    typeof book.created_at === 'string' &&
    typeof book.updated_at === 'string' &&
    typeof book.owner_id === 'string' &&
    Array.isArray(book.toc_items) &&
    typeof book.published === 'boolean' &&
    typeof book.metadata === 'object' &&
    book.metadata !== null
  );
}

/**
 * Type guard to check if an object is a valid Question
 *
 * @param obj - Object to check
 * @returns True if object is a valid Question
 */
export function isQuestion(obj: unknown): obj is Question {
  if (typeof obj !== 'object' || obj === null) return false;

  const q = obj as Record<string, unknown>;

  return (
    typeof q.id === 'string' &&
    typeof q.book_id === 'string' &&
    typeof q.chapter_id === 'string' &&
    typeof q.question_text === 'string' &&
    isQuestionType(q.question_type) &&
    isQuestionDifficulty(q.difficulty) &&
    typeof q.category === 'string' &&
    typeof q.order === 'number' &&
    typeof q.generated_at === 'string'
  );
}

/**
 * Type guard to check if an object is a valid QuestionResponse
 *
 * @param obj - Object to check
 * @returns True if object is a valid QuestionResponse
 */
export function isQuestionResponse(obj: unknown): obj is QuestionResponse {
  if (typeof obj !== 'object' || obj === null) return false;

  const qr = obj as Record<string, unknown>;

  return (
    typeof qr.id === 'string' &&
    typeof qr.question_id === 'string' &&
    typeof qr.user_id === 'string' &&
    typeof qr.response_text === 'string' &&
    typeof qr.word_count === 'number' &&
    typeof qr.created_at === 'string' &&
    typeof qr.updated_at === 'string'
  );
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Calculate the total word count for a book from its chapters
 *
 * @param book - Book with toc_items
 * @returns Total word count across all chapters
 *
 * @example
 * ```typescript
 * const totalWords = calculateBookWordCount(book);
 * console.log(`Total words: ${totalWords.toLocaleString()}`);
 * ```
 */
export function calculateBookWordCount(book: BookResponse): number {
  return book.toc_items.reduce((total, item) => total + item.word_count, 0);
}

/**
 * Calculate completion percentage for a book based on chapter statuses
 *
 * @param book - Book with toc_items
 * @returns Completion percentage (0-100)
 *
 * @example
 * ```typescript
 * const progress = calculateBookProgress(book);
 * console.log(`Book is ${progress}% complete`);
 * ```
 */
export function calculateBookProgress(book: BookResponse): number {
  if (book.toc_items.length === 0) return 0;

  const completedChapters = book.toc_items.filter(
    (item) => item.status === ChapterStatus.COMPLETED || item.status === ChapterStatus.PUBLISHED
  ).length;

  return Math.round((completedChapters / book.toc_items.length) * 100);
}

/**
 * Convert BookResponse to BookProject (legacy format)
 *
 * @param book - Modern BookResponse
 * @returns Legacy BookProject format
 *
 * @deprecated Use BookResponse directly. This is for backward compatibility only.
 *
 * @example
 * ```typescript
 * const legacyBook = toBookProject(bookResponse);
 * ```
 */
export function toBookProject(book: BookResponse): BookProject {
  return {
    ...book,
    chapters: book.toc_items.length,
    progress: calculateBookProgress(book),
    word_count: calculateBookWordCount(book),
  };
}

/**
 * Get chapter by ID from a book's table of contents
 *
 * @param book - Book with toc_items
 * @param chapterId - ID of the chapter to find
 * @returns TocItem if found, undefined otherwise
 *
 * @example
 * ```typescript
 * const chapter = getChapterById(book, 'chapter-123');
 * if (chapter) {
 *   console.log(`Found: ${chapter.title}`);
 * }
 * ```
 */
export function getChapterById(book: BookResponse, chapterId: string): TocItem | undefined {
  return book.toc_items.find((item) => item.id === chapterId);
}

/**
 * Get all chapters at a specific level
 *
 * @param book - Book with toc_items
 * @param level - Hierarchical level (1 = chapter, 2 = section, etc.)
 * @returns Array of TocItems at the specified level
 *
 * @example
 * ```typescript
 * const chapters = getChaptersByLevel(book, 1); // Get all top-level chapters
 * const sections = getChaptersByLevel(book, 2); // Get all sections
 * ```
 */
export function getChaptersByLevel(book: BookResponse, level: number): TocItem[] {
  return book.toc_items.filter((item) => item.level === level);
}

/**
 * Get child chapters of a parent chapter
 *
 * @param book - Book with toc_items
 * @param parentId - ID of the parent chapter
 * @returns Array of child TocItems
 *
 * @example
 * ```typescript
 * const sections = getChildChapters(book, 'chapter-1');
 * console.log(`Chapter 1 has ${sections.length} sections`);
 * ```
 */
export function getChildChapters(book: BookResponse, parentId: string): TocItem[] {
  return book.toc_items.filter((item) => item.parent_id === parentId);
}

/**
 * Sort chapters by their order property
 *
 * @param chapters - Array of TocItems to sort
 * @returns Sorted array (does not mutate original)
 *
 * @example
 * ```typescript
 * const sortedChapters = sortChaptersByOrder(book.toc_items);
 * ```
 */
export function sortChaptersByOrder(chapters: TocItem[]): TocItem[] {
  return [...chapters].sort((a, b) => a.order - b.order);
}
