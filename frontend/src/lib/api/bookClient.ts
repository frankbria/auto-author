'use client';

import { BookProject } from '@/components/BookCard';
// We don't need the TOC QuestionResponse import since we're using the one from chapter-questions
import { ChapterStatus } from '@/types/chapter-tabs';
// Import only what we use to satisfy linting
import {
  QuestionResponse,
  QuestionProgressResponse,
  GenerateQuestionsRequest,
  GenerateQuestionsResponse,
  QuestionListResponse,
  QuestionResponseRequest,
  QuestionRatingRequest,
  QuestionType
} from '@/types/chapter-questions';

/**
 * API client for book operations
 * This would be expanded with more operations and proper authentication
 * as the backend is developed.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export class BookClient {
  private baseUrl: string;
  private authToken?: string;
  
  constructor(baseUrl = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }
  
  /**
   * Set authentication token for API calls
   */
  public setAuthToken(token: string) {
    this.authToken = token;
  }
  
  /**
   * Get default headers for API requests
   */
  private getHeaders() {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    
    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`;
    }
    
    return headers;
  }
  
  /**
   * Fetch all books for the current user
   */
  public async getUserBooks(): Promise<BookProject[]> {
    const response = await fetch(`${this.baseUrl}/books`, {
      headers: this.getHeaders(),
      credentials: 'include',
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch books: ${response.status}`);
    }
    return response.json();
  }

  /**
   * Fetch a single book by ID
   */
  public async getBook(bookId: string): Promise<BookProject> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}`, {
      headers: this.getHeaders(),
      credentials: 'include',
    });
    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        throw new Error('You are not authorized to view this book. Please check your login or permissions.');
      }
      throw new Error(`Failed to fetch book: ${response.status}`);
    }
    return response.json();
  }

  /**
   * Create a new book
   */
  public async createBook(bookData: {
    title: string;
    subtitle?: string;
    description?: string;
    genre?: string;
    target_audience?: string;
    cover_image_url?: string;
  }): Promise<BookProject> {
    const response = await fetch(`${this.baseUrl}/books`, {
      method: 'POST',
      headers: this.getHeaders(),
      credentials: 'include',
      body: JSON.stringify(bookData),
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to create book: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Update an existing book
   */
  public async updateBook(
    bookId: string,
    bookData: { title?: string; description?: string; subtitle?: string; genre?: string; target_audience?: string; cover_image_url?: string }
  ): Promise<BookProject> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}`, {
      method: 'PATCH',
      headers: this.getHeaders(),
      credentials: 'include',
      body: JSON.stringify(bookData),
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to update book: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Delete a book by ID
   */
  public async deleteBook(bookId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}`, {
      method: 'DELETE',
      headers: this.getHeaders(),
      credentials: 'include',
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to delete book: ${response.status} ${error}`);
    }
  }

  /**
   * Check if a book's summary is ready for TOC generation
   */
  public async checkTocReadiness(bookId: string): Promise<{
    is_ready_for_toc: boolean;
    confidence_score: number;
    analysis: string;
    suggestions: string[];
    word_count: number;
    character_count: number;
    meets_minimum_requirements: boolean;
  }> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}/toc-readiness`, {
      headers: this.getHeaders(),
      credentials: 'include',
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to check TOC readiness: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Analyze the book summary using AI to determine readiness for TOC generation
   */
  public async analyzeSummary(bookId: string): Promise<{
    book_id: string;
    analysis: {
      is_ready_for_toc: boolean;
      confidence_score: number;
      analysis: string;
      suggestions: string[];
      word_count: number;
      character_count: number;
      meets_minimum_requirements: boolean;
    };
    analyzed_at: string;
  }> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}/analyze-summary`, {
      method: 'POST',
      headers: this.getHeaders(),
      credentials: 'include',
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to analyze summary: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Generate clarifying questions for TOC creation
   */
  public async generateQuestions(bookId: string): Promise<{
    questions: string[];
  }> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}/generate-questions`, {
      method: 'POST',
      headers: this.getHeaders(),
      credentials: 'include',
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to generate questions: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Generate TOC from summary and question responses
   */
  public async generateToc(bookId: string, questionResponses: Array<{
    question: string;
    answer: string;
  }>): Promise<{
    toc: {
      chapters: Array<{
        id: string;
        title: string;
        description: string;
        level: number;
        order: number;
        subchapters: Array<{
          id: string;
          title: string;
          description: string;
          level: number;
          order: number;
        }>;
      }>;
      total_chapters: number;
      estimated_pages: number;
      structure_notes: string;
    };
    success: boolean;
    chapters_count: number;
    has_subchapters: boolean;
  }> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}/generate-toc`, {
      method: 'POST',
      headers: this.getHeaders(),
      credentials: 'include',
      body: JSON.stringify({ question_responses: questionResponses }),
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to generate TOC: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Get current TOC for a book
   */
  public async getToc(bookId: string): Promise<{
    toc: {
      chapters: Array<{
        id: string;
        title: string;
        description: string;
        level: number;
        order: number;
        subchapters: Array<{
          id: string;
          title: string;
          description: string;
          level: number;
          order: number;
        }>;
      }>;
      total_chapters: number;
      estimated_pages: number;
      structure_notes: string;
    } | null;
  }> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}/toc`, {
      headers: this.getHeaders(),
      credentials: 'include',
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to get TOC: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Update TOC for a book
   */
  public async updateToc(bookId: string, toc: {
    chapters: Array<{
      id: string;
      title: string;
      description: string;
      level: number;
      order: number;
      subchapters: Array<{
        id: string;
        title: string;
        description: string;
        level: number;
        order: number;
      }>;
    }>;
    total_chapters: number;
    estimated_pages: number;
    structure_notes: string;  }): Promise<{
    toc: {
      chapters: Array<{
        id: string;
        title: string;
        description: string;
        level: number;
        order: number;
        subchapters: Array<{
          id: string;
          title: string;
          description: string;
          level: number;
          order: number;
        }>;
      }>;
      total_chapters: number;
      estimated_pages: number;
      structure_notes: string;
    };
    success: boolean;
  }> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}/toc`, {
      method: 'PUT',
      headers: this.getHeaders(),
      credentials: 'include',
      body: JSON.stringify({ toc }),
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to update TOC: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Get the summary and revision history for a book
   */
  public async getBookSummary(bookId: string): Promise<{ summary: string; summary_history?: unknown[] }> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}/summary`, {
      headers: this.getHeaders(),
      credentials: 'include',
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to fetch book summary: ${response.status} ${error}`);
    }
    return response.json();
  }
  /**
   * Save/update the summary for a book
   */
  public async saveBookSummary(bookId: string, summary: string): Promise<{ summary: string; success: boolean }> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}/summary`, {
      method: 'PUT',
      headers: this.getHeaders(),
      credentials: 'include',
      body: JSON.stringify({ summary }),
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to save book summary: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Save question responses for TOC generation
   */
  public async saveQuestionResponses(bookId: string, responses: QuestionResponse[]): Promise<{
    book_id: string;
    responses_saved: number;
    answered_at: string;
    ready_for_toc_generation: boolean;
  }> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}/question-responses`, {
      method: 'PUT',
      headers: this.getHeaders(),
      credentials: 'include',
      body: JSON.stringify({ responses }),
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to save question responses: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Get saved question responses for a book
   */
  public async getQuestionResponses(bookId: string): Promise<{
    responses: QuestionResponse[];
    answered_at?: string;
    status: string;
  }> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}/question-responses`, {
      method: 'GET',
      headers: this.getHeaders(),
      credentials: 'include',
    });
    if (!response.ok) {
      if (response.status === 404) {
        return { responses: [], status: 'not_provided' };
      }
      const error = await response.text();
      throw new Error(`Failed to get question responses: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Save chapter content
   */
  public async saveChapterContent(
    bookId: string, 
    chapterId: string, 
    content: string,
    autoUpdateMetadata: boolean = true
  ): Promise<{
    book_id: string;
    chapter_id: string;
    success: boolean;
    message: string;
    metadata_updated: boolean;
  }> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}/chapters/${chapterId}/content`, {
      method: 'PATCH',
      headers: this.getHeaders(),
      credentials: 'include',
      body: JSON.stringify({ 
        content,
        auto_update_metadata: autoUpdateMetadata
      }),
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to save chapter content: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Get chapter content
   */
  public async getChapterContent(
    bookId: string,
    chapterId: string,
    includeMetadata: boolean = true,
    trackAccess: boolean = true
  ): Promise<{
    content: string;
    chapter_id: string;
    book_id: string;
    metadata?: {
      word_count: number;
      last_modified: string;
      status: string;
      estimated_reading_time: number;
    };
  }> {
    const params = new URLSearchParams({
      include_metadata: includeMetadata.toString(),
      track_access: trackAccess.toString()
    });
    
    const response = await fetch(`${this.baseUrl}/books/${bookId}/chapters/${chapterId}/content?${params}`, {
      method: 'GET',
      headers: this.getHeaders(),
      credentials: 'include',
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to get chapter content: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Get chapters metadata for tab management
   */
  public async getChaptersMetadata(bookId: string, includeContentStats = true): Promise<{
    book_id: string;
    chapters: Array<{
      id: string;
      title: string;
      description: string;
      level: number;
      order: number;
      status: string;
      word_count: number;
      estimated_reading_time: number;
      last_modified: string;
    }>;
    total_chapters: number;
    completion_stats: {
      draft: number;
      in_progress: number;
      completed: number;
      published: number;
    };
    last_active_chapter?: string;
  }> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}/chapters/metadata?include_content_stats=${includeContentStats}`, {
      headers: this.getHeaders(),
      credentials: 'include',
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to get chapters metadata: ${response.status} ${error}`);
    }
    return response.json();
  }
  /**
   * Update chapter status
   */
  public async updateChapterStatus(bookId: string, chapterId: string, status: ChapterStatus): Promise<void> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}/chapters/bulk-status`, {
      method: 'PATCH',
      headers: this.getHeaders(),
      credentials: 'include',
      body: JSON.stringify({
        chapter_ids: [chapterId],
        status,
        update_timestamp: true
      })
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to update chapter status: ${response.status} ${error}`);
    }
    return response.json();
  }
  /**
   * Update bulk chapter status
   */
  public async updateBulkChapterStatus(bookId: string, chapterIds: string[], status: ChapterStatus): Promise<void> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}/chapters/bulk-status`, {
      method: 'PATCH',
      headers: this.getHeaders(),
      credentials: 'include',
      body: JSON.stringify({
        chapter_ids: chapterIds,
        status,
        update_timestamp: true
      })
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to update bulk chapter status: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Save tab state for chapter navigation
   */
  public async saveTabState(bookId: string, tabState: {
    active_chapter_id: string | null;
    open_tab_ids: string[];
    tab_order: string[];
  }): Promise<void> {
    const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    const response = await fetch(`${this.baseUrl}/books/${bookId}/chapters/tab-state`, {
      method: 'POST',
      headers: this.getHeaders(),
      credentials: 'include',
      body: JSON.stringify({
        ...tabState,
        session_id: sessionId
      })
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to save tab state: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Get saved tab state for chapter navigation
   */
  public async getTabState(bookId: string, sessionId?: string): Promise<{
    active_chapter_id: string | null;
    open_tab_ids: string[];
    tab_order: string[];
    session_id?: string;
  } | null> {
    const params = sessionId ? `?session_id=${sessionId}` : '';
    const response = await fetch(`${this.baseUrl}/books/${bookId}/chapters/tab-state${params}`, {
      headers: this.getHeaders(),
      credentials: 'include',
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to get tab state: ${response.status} ${error}`);
    }
    return response.json();
  }

  // ============= Interview-Style Questions Methods =============

  /**
   * Generate AI draft for a chapter
   */
  public async generateChapterDraft(
    bookId: string,
    chapterId: string,
    data: {
      question_responses: Array<{ question: string; answer: string }>;
      writing_style?: string;
      target_length?: number;
    }
  ): Promise<{
    success: boolean;
    book_id: string;
    chapter_id: string;
    draft: string;
    metadata: {
      word_count: number;
      estimated_reading_time: number;
      generated_at: string;
      model_used: string;
      writing_style: string;
      target_length: number;
      actual_length: number;
    };
    suggestions: string[];
    message: string;
  }> {
    const response = await fetch(
      `${this.baseUrl}/books/${bookId}/chapters/${chapterId}/generate-draft`,
      {
        method: 'POST',
        headers: this.getHeaders(),
        credentials: 'include',
        body: JSON.stringify(data),
      }
    );
    
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to generate draft: ${response.status} ${error}`);
    }
    
    return response.json();
  }

  /**
   * Generate interview-style questions for a specific chapter
   */
  public async generateChapterQuestions(
    bookId: string,
    chapterId: string,
    options: GenerateQuestionsRequest = {}
  ): Promise<GenerateQuestionsResponse> {
    const response = await fetch(
      `${this.baseUrl}/books/${bookId}/chapters/${chapterId}/generate-questions`,
      {
        method: 'POST',
        headers: this.getHeaders(),
        credentials: 'include',
        body: JSON.stringify(options),
      }
    );
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to generate questions: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Get questions for a chapter with optional filtering
   */
  public async getChapterQuestions(
    bookId: string,
    chapterId: string,
    options: {
      status?: string;
      category?: string;
      questionType?: QuestionType;
      page?: number;
      limit?: number;
    } = {}
  ): Promise<QuestionListResponse> {
    const params = new URLSearchParams();
    if (options.status) params.append('status', options.status);
    if (options.category) params.append('category', options.category);
    if (options.questionType) params.append('question_type', options.questionType);
    if (options.page) params.append('page', options.page.toString());
    if (options.limit) params.append('limit', options.limit.toString());

    const response = await fetch(
      `${this.baseUrl}/books/${bookId}/chapters/${chapterId}/questions?${params}`,
      {
        headers: this.getHeaders(),
        credentials: 'include',
      }
    );
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to get questions: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Save or update a response to a question
   */
  public async saveQuestionResponse(
    bookId: string,
    chapterId: string,
    questionId: string,
    responseData: QuestionResponseRequest
  ): Promise<{ response: QuestionResponse; success: boolean; message: string }> {
    const response = await fetch(
      `${this.baseUrl}/books/${bookId}/chapters/${chapterId}/questions/${questionId}/response`,
      {
        method: 'PUT',
        headers: this.getHeaders(),
        credentials: 'include',
        body: JSON.stringify(responseData),
      }
    );
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to save question response: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Get a response to a specific question
   */
  public async getQuestionResponse(
    bookId: string,
    chapterId: string,
    questionId: string
  ): Promise<{ response: QuestionResponse | null; has_response: boolean; success: boolean }> {
    const response = await fetch(
      `${this.baseUrl}/books/${bookId}/chapters/${chapterId}/questions/${questionId}/response`,
      {
        headers: this.getHeaders(),
        credentials: 'include',
      }
    );
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to get question response: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Rate a question's relevance and quality
   */
  public async rateQuestion(
    bookId: string,
    chapterId: string,
    questionId: string,
    ratingData: QuestionRatingRequest
  ): Promise<{ rating: { id: string; question_id: string; rating: number; feedback?: string; created_at: string }; success: boolean; message: string }> {
    const response = await fetch(
      `${this.baseUrl}/books/${bookId}/chapters/${chapterId}/questions/${questionId}/rating`,
      {
        method: 'POST',
        headers: this.getHeaders(),
        credentials: 'include',
        body: JSON.stringify(ratingData),
      }
    );
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to rate question: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Get progress information for a chapter's questions
   */
  public async getChapterQuestionProgress(
    bookId: string,
    chapterId: string
  ): Promise<QuestionProgressResponse> {
    const response = await fetch(
      `${this.baseUrl}/books/${bookId}/chapters/${chapterId}/question-progress`,
      {
        headers: this.getHeaders(),
        credentials: 'include',
      }
    );
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to get question progress: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Regenerate questions for a chapter, optionally preserving existing responses
   */
  public async regenerateChapterQuestions(
    bookId: string,
    chapterId: string,
    options: GenerateQuestionsRequest = {},
    preserveResponses: boolean = true
  ): Promise<GenerateQuestionsResponse> {
    const response = await fetch(
      `${this.baseUrl}/books/${bookId}/chapters/${chapterId}/regenerate-questions?preserve_responses=${preserveResponses}`,
      {
        method: 'POST',
        headers: this.getHeaders(),
        credentials: 'include',
        body: JSON.stringify(options),
      }
    );
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to regenerate questions: ${response.status} ${error}`);
    }
    return response.json();
  }



  /**
   * Export book as PDF
   */
  public async exportPDF(
    bookId: string,
    options?: {
      includeEmptyChapters?: boolean;
      pageSize?: 'letter' | 'A4';
    }
  ): Promise<Blob> {
    const params = new URLSearchParams();
    if (options?.includeEmptyChapters !== undefined) {
      params.append('include_empty_chapters', options.includeEmptyChapters.toString());
    }
    if (options?.pageSize) {
      params.append('page_size', options.pageSize);
    }

    const response = await fetch(
      `${this.baseUrl}/books/${bookId}/export/pdf?${params.toString()}`,
      {
        headers: this.getHeaders(),
        credentials: 'include',
      }
    );
    
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to export PDF: ${response.status} ${error}`);
    }
    
    return response.blob();
  }

  /**
   * Export book as DOCX
   */
  public async exportDOCX(
    bookId: string,
    options?: {
      includeEmptyChapters?: boolean;
    }
  ): Promise<Blob> {
    const params = new URLSearchParams();
    if (options?.includeEmptyChapters !== undefined) {
      params.append('include_empty_chapters', options.includeEmptyChapters.toString());
    }

    const response = await fetch(
      `${this.baseUrl}/books/${bookId}/export/docx?${params.toString()}`,
      {
        headers: this.getHeaders(),
        credentials: 'include',
      }
    );
    
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to export DOCX: ${response.status} ${error}`);
    }
    
    return response.blob();
  }

  /**
   * Get available export formats and book statistics
   */
  public async getExportFormats(bookId: string): Promise<{
    formats: Array<{
      format: string;
      name: string;
      description: string;
      mime_type: string;
      extension: string;
      available: boolean;
      options?: Record<string, any>;
    }>;
    book_stats: {
      total_chapters: number;
      chapters_with_content: number;
      total_word_count: number;
      estimated_pages: number;
    };
  }> {
    const response = await fetch(
      `${this.baseUrl}/books/${bookId}/export/formats`,
      {
        headers: this.getHeaders(),
        credentials: 'include',
      }
    );
    
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to get export formats: ${response.status} ${error}`);
    }
    
    return response.json();
  }


  /**
   * Create a new chapter in a book
   */
  public async createChapter(bookId: string, chapterData: {
    title: string;
    content?: string;
    order?: number;
  }): Promise<{
    id: string;
    title: string;
    content: string;
    order: number;
    status: string;
    created_at: string;
    updated_at: string;
  }> {
    const response = await fetch(
      `${this.baseUrl}/books/${bookId}/chapters`,
      {
        method: 'POST',
        headers: this.getHeaders(),
        credentials: 'include',
        body: JSON.stringify(chapterData),
      }
    );
    
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to create chapter: ${response.status} ${error}`);
    }
    
    return await response.json();
  }

  /**
   * Delete a chapter from a book
   */
  public async deleteChapter(bookId: string, chapterId: string): Promise<void> {
    const response = await fetch(
      `${this.baseUrl}/books/${bookId}/chapters/${chapterId}`,
      {
        method: 'DELETE',
        headers: this.getHeaders(),
        credentials: 'include',
      }
    );
    
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to delete chapter: ${response.status} ${error}`);
    }
  }
}

// Create a singleton instance for use throughout the app
export const bookClient = new BookClient();

export default bookClient;
