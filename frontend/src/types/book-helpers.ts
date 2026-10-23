/**
 * Book Type Definitions: helper functions
 *
 * Re-exported from `@/types/book`.
 *
 * @module types/book-helpers
 */

import { ChapterStatus } from './book-enums';
import type { TocItem } from './book-toc';
import type { BookResponse, BookProject } from './book-model';

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * What the two calculations below read: each chapter's status and word count.
 * A `BookResponse` has it, and so does what `getChaptersMetadata` returns, which
 * is how the book page's stats panel uses the same sums as the book cards (#833).
 */
export interface ChapterCounts {
  toc_items: ReadonlyArray<{ status: string; word_count: number }>;
}

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
export function calculateBookWordCount(book: ChapterCounts): number {
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
export function calculateBookProgress(book: ChapterCounts): number {
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
