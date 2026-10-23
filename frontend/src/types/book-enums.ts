/**
 * Book Type Definitions: enums
 *
 * Re-exported from `@/types/book`.
 *
 * @module types/book-enums
 */

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
