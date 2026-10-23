/**
 * Book Type Definitions: type guards and validation utilities
 *
 * Re-exported from `@/types/book`.
 *
 * @module types/book-guards
 */

import { ChapterStatus, QuestionType, QuestionDifficulty } from './book-enums';
import type { TocItem } from './book-toc';
import type { Question, QuestionResponse } from './book-questions';
import type { BookResponse } from './book-model';

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
