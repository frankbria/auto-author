/**
 * Book Type Definitions: chapter question and response types
 *
 * Re-exported from `@/types/book`.
 *
 * @module types/book-questions
 */

import { QuestionType, QuestionDifficulty, ResponseStatus } from './book-enums';

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
