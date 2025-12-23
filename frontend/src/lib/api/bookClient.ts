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
import { handleAIServiceError, AIServiceResult } from '@/lib/api/aiErrorHandler';

/**
 * API client for book operations
 *
 * Provides a comprehensive interface for interacting with the Auto-Author backend API.
 * All methods include automatic authentication header injection and consistent error handling.
 *
 * @class BookClient
 * @see {@link frontend/src/types/book.ts} - Type definitions
 * @see {@link backend/app/routers/books.py} - Backend API routes
 *
 * @example
 * ```typescript
 * // Initialize client (typically done once)
 * import { bookClient } from '@/lib/api/bookClient';
 *
 * // Set auth token (from Clerk or other auth provider)
 * bookClient.setAuthToken(authToken);
 *
 * // Make API calls
 * const books = await bookClient.getUserBooks();
 * const book = await bookClient.getBook(bookId);
 * ```
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export class BookClient {
  private baseUrl: string;
  private authToken?: string;
  private tokenProvider?: () => Promise<string | null>;

  /**
   * Creates a new BookClient instance
   *
   * @param baseUrl - Base URL for the API (defaults to NEXT_PUBLIC_API_URL or localhost)
   *
   * @example
   * ```typescript
   * // Use default URL
   * const client = new BookClient();
   *
   * // Use custom URL
   * const client = new BookClient('https://api.example.com/v1');
   * ```
   */
  constructor(baseUrl = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Set authentication token for API calls
   *
   * All subsequent API calls will include this token in the Authorization header.
   * Call this method after user authentication to enable authenticated requests.
   *
   * @param token - JWT or Bearer token from authentication provider
   *
   * @example
   * ```typescript
   * // With Clerk
   * const { getToken } = useAuth();
   * const token = await getToken();
   * bookClient.setAuthToken(token);
   *
   * // Manual token
   * bookClient.setAuthToken('eyJhbGc...');
   * ```
   */
  public setAuthToken(token: string) {
    this.authToken = token;
  }

  /**
   * Set a token provider function for automatic token refresh
   *
   * This allows the client to fetch fresh tokens before each API call,
   * preventing token expiration issues during long-running operations.
   *
   * @param provider - Function that returns a promise resolving to a token or null
   *
   * @example
   * ```typescript
   * // With Clerk
   * const { getToken } = useAuth();
   * bookClient.setTokenProvider(getToken);
   * ```
   */
  public setTokenProvider(provider: () => Promise<string | null>) {
    this.tokenProvider = provider;
  }

  /**
   * Get authentication token
   *
   * Internal method that returns either the cached token or fetches a fresh one
   * from the token provider if available.
   *
   * @private
   * @returns Promise resolving to token string or undefined
   */
  private async getAuthToken(): Promise<string | undefined> {
    if (this.tokenProvider) {
      const token = await this.tokenProvider();
      return token || undefined;
    }
    return this.authToken;
  }

  /**
   * Get default headers for API requests
   *
   * Internal method that constructs headers for all API calls.
   * Includes Content-Type and Authorization headers.
   *
   * @private
   * @returns Promise resolving to headers object with Content-Type and optional Authorization
   */
  private async getHeaders(): Promise<HeadersInit> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    const token = await this.getAuthToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  }

  /**
   * Fetch all books for the current authenticated user
   *
   * Retrieves a list of all books owned by or shared with the current user.
   * Results include basic book metadata and TOC information.
   *
   * @returns Promise resolving to array of book projects
   *
   * @throws {Error} When the request fails or user is not authenticated
   *   - 401: User is not authenticated (missing or invalid token)
   *   - 500: Server error occurred
   *   - Network errors: Connection issues, timeout
   *
   * @example
   * ```typescript
   * // Fetch user's books
   * const books = await bookClient.getUserBooks();
   * console.log(`Found ${books.length} books`);
   *
   * // With error handling
   * try {
   *   const books = await bookClient.getUserBooks();
   *   books.forEach(book => console.log(book.title));
   * } catch (error) {
   *   if (error.message.includes('401')) {
   *     console.error('Please log in to view books');
   *   } else {
   *     console.error('Failed to load books:', error.message);
   *   }
   * }
   * ```
   */
  public async getUserBooks(): Promise<BookProject[]> {
    const response = await fetch(`${this.baseUrl}/books/`, {  // Added trailing slash
      headers: await this.getHeaders(),
      credentials: 'include',
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch books: ${response.status}`);
    }
    return response.json();
  }

  /**
   * Fetch a single book by its unique identifier
   *
   * Retrieves complete book data including all metadata, chapters, and TOC structure.
   * Requires user to be authenticated and have access to the book (owner or collaborator).
   *
   * @param bookId - Unique identifier for the book
   * @returns Promise resolving to book project data
   *
   * @throws {Error} When the request fails or access is denied
   *   - 401: User is not authenticated
   *   - 403: User does not have permission to view this book
   *   - 404: Book not found
   *   - 500: Server error occurred
   *
   * @example
   * ```typescript
   * // Fetch specific book
   * const book = await bookClient.getBook('book-123');
   * console.log(`Book: ${book.title}, Chapters: ${book.chapters}`);
   *
   * // With error handling
   * try {
   *   const book = await bookClient.getBook(bookId);
   *   console.log(book.title);
   * } catch (error) {
   *   if (error.message.includes('401') || error.message.includes('403')) {
   *     console.error('Access denied to book');
   *   } else if (error.message.includes('404')) {
   *     console.error('Book not found');
   *   }
   * }
   * ```
   */
  public async getBook(bookId: string): Promise<BookProject> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}`, {
      headers: await this.getHeaders(),
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
   *
   * Creates a new book project with the provided metadata.
   * The authenticated user becomes the owner of the book.
   * Title is required, all other fields are optional.
   *
   * @param bookData - Book creation data
   * @param bookData.title - Book title (1-100 characters, required)
   * @param bookData.subtitle - Optional subtitle (max 255 characters)
   * @param bookData.description - Optional description (max 5000 characters)
   * @param bookData.genre - Optional genre classification
   * @param bookData.target_audience - Optional target audience description
   * @param bookData.cover_image_url - Optional URL to cover image
   * @returns Promise resolving to the created book project
   *
   * @throws {Error} When creation fails
   *   - 400: Invalid request data
   *   - 401: User is not authenticated
   *   - 422: Validation error (e.g., title too short/long)
   *   - 500: Server error occurred
   *
   * @example
   * ```typescript
   * // Minimal book creation
   * const newBook = await bookClient.createBook({
   *   title: 'My First Book'
   * });
   *
   * // Complete book creation
   * const detailedBook = await bookClient.createBook({
   *   title: 'The Complete Guide',
   *   subtitle: 'Everything You Need to Know',
   *   description: 'A comprehensive guide covering all aspects...',
   *   genre: 'Non-fiction',
   *   target_audience: 'Professionals and enthusiasts',
   *   cover_image_url: 'https://example.com/cover.jpg'
   * });
   *
   * // With error handling
   * try {
   *   const book = await bookClient.createBook({ title: bookTitle });
   *   console.log('Book created:', book.id);
   * } catch (error) {
   *   if (error.message.includes('422')) {
   *     console.error('Invalid book data:', error.message);
   *   }
   * }
   * ```
   */
  public async createBook(bookData: {
    title: string;
    subtitle?: string;
    description?: string;
    genre?: string;
    target_audience?: string;
    cover_image_url?: string;
  }): Promise<BookProject> {
    const response = await fetch(`${this.baseUrl}/books/`, {
      method: 'POST',
      headers: await this.getHeaders(),
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
   * Update an existing book's metadata
   *
   * Updates one or more fields of an existing book.
   * Only provided fields will be updated (partial update).
   * Requires user to be the book owner or have editor/co-author permissions.
   *
   * @param bookId - Unique identifier for the book
   * @param bookData - Fields to update (all optional)
   * @param bookData.title - New book title
   * @param bookData.subtitle - New subtitle
   * @param bookData.description - New description
   * @param bookData.genre - New genre
   * @param bookData.target_audience - New target audience
   * @param bookData.cover_image_url - New cover image URL
   * @returns Promise resolving to the updated book project
   *
   * @throws {Error} When update fails
   *   - 400: Invalid request data
   *   - 401: User is not authenticated
   *   - 403: User does not have permission to edit this book
   *   - 404: Book not found
   *   - 422: Validation error
   *   - 500: Server error occurred
   *
   * @example
   * ```typescript
   * // Update single field
   * await bookClient.updateBook(bookId, {
   *   title: 'Updated Title'
   * });
   *
   * // Update multiple fields
   * await bookClient.updateBook(bookId, {
   *   title: 'New Title',
   *   description: 'Updated description',
   *   genre: 'Fiction'
   * });
   *
   * // With error handling
   * try {
   *   const updatedBook = await bookClient.updateBook(bookId, updates);
   *   console.log('Book updated:', updatedBook.title);
   * } catch (error) {
   *   if (error.message.includes('403')) {
   *     console.error('No permission to edit this book');
   *   } else if (error.message.includes('404')) {
   *     console.error('Book not found');
   *   }
   * }
   * ```
   */
  public async updateBook(
    bookId: string,
    bookData: { title?: string; description?: string; subtitle?: string; genre?: string; target_audience?: string; cover_image_url?: string }
  ): Promise<BookProject> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}`, {
      method: 'PATCH',
      headers: await this.getHeaders(),
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
   * Permanently delete a book
   *
   * Deletes a book and ALL associated data including:
   * - All chapters and their content
   * - Table of contents structure
   * - Question responses
   * - Tab states and preferences
   * - Analytics and access logs
   *
   * ⚠️ **WARNING**: This operation is irreversible. All data will be permanently lost.
   *
   * Requires user to be the book owner (collaborators cannot delete books).
   *
   * @param bookId - Unique identifier for the book to delete
   * @returns Promise that resolves when deletion is complete
   *
   * @throws {Error} When deletion fails
   *   - 401: User is not authenticated
   *   - 403: User is not the book owner (only owners can delete)
   *   - 404: Book not found
   *   - 500: Server error occurred
   *
   * @example
   * ```typescript
   * // Delete a book (use with caution!)
   * await bookClient.deleteBook(bookId);
   * console.log('Book deleted successfully');
   *
   * // With user confirmation
   * if (confirm('Are you sure? This cannot be undone!')) {
   *   try {
   *     await bookClient.deleteBook(bookId);
   *     router.push('/dashboard');
   *   } catch (error) {
   *     if (error.message.includes('403')) {
   *       console.error('Only the book owner can delete this book');
   *     } else {
   *       console.error('Failed to delete book:', error.message);
   *     }
   *   }
   * }
   *
   * // Best practice: Use DeleteBookModal component for confirmation
   * ```
   *
   * @see {@link frontend/src/components/books/DeleteBookModal.tsx} - UI component with type-to-confirm
   */
  public async deleteBook(bookId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}`, {
      method: 'DELETE',
      headers: await this.getHeaders(),
      credentials: 'include',
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to delete book: ${response.status} ${error}`);
    }
  }

  /**
   * Check if a book's summary is ready for TOC generation
   *
   * Evaluates the book summary to determine if it contains sufficient detail
   * for AI-powered table of contents generation. Uses cached analysis if available.
   *
   * @param bookId - Unique identifier for the book
   * @returns Promise resolving to readiness assessment
   *
   * @throws {Error} When the request fails
   *   - 401: User is not authenticated
   *   - 403: User does not have access to this book
   *   - 404: Book not found or has no summary
   *   - 500: Server error occurred
   *
   * @example
   * ```typescript
   * // Check readiness
   * const readiness = await bookClient.checkTocReadiness(bookId);
   *
   * if (readiness.is_ready_for_toc) {
   *   console.log('Ready for TOC generation!');
   *   console.log(`Confidence: ${readiness.confidence_score}`);
   * } else {
   *   console.log('Summary needs more detail:');
   *   readiness.suggestions.forEach(s => console.log(`- ${s}`));
   * }
   *
   * // Check minimum requirements
   * if (!readiness.meets_minimum_requirements) {
   *   alert(`Summary too short. Current: ${readiness.word_count} words. Need: 100+ words.`);
   * }
   * ```
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
      headers: await this.getHeaders(),
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
   *
   * Performs a new AI-powered analysis of the book summary to assess whether
   * it's ready for TOC generation. This triggers a fresh analysis and updates
   * the cached readiness check results.
   *
   * The AI evaluates:
   * - Summary length and completeness
   * - Presence of key narrative elements
   * - Structural clarity
   * - Sufficient detail for chapter breakdown
   *
   * @param bookId - Unique identifier for the book
   * @returns Promise resolving to detailed analysis results
   *
   * @throws {Error} When analysis fails
   *   - 400: Invalid request (e.g., book has no summary)
   *   - 401: User is not authenticated
   *   - 403: User does not have access to this book
   *   - 404: Book not found
   *   - 500: Server error or AI service unavailable
   *
   * @example
   * ```typescript
   * // Trigger new analysis
   * const analysis = await bookClient.analyzeSummary(bookId);
   *
   * console.log(`Analysis completed at: ${analysis.analyzed_at}`);
   * console.log(`Ready: ${analysis.analysis.is_ready_for_toc}`);
   * console.log(`Confidence: ${analysis.analysis.confidence_score}`);
   * console.log(`Feedback: ${analysis.analysis.analysis}`);
   *
   * // Show suggestions if not ready
   * if (!analysis.analysis.is_ready_for_toc) {
   *   analysis.analysis.suggestions.forEach(suggestion => {
   *     console.log(`💡 ${suggestion}`);
   *   });
   * }
   *
   * // With error handling
   * try {
   *   const analysis = await bookClient.analyzeSummary(bookId);
   *   // ... use analysis
   * } catch (error) {
   *   if (error.message.includes('400')) {
   *     alert('Please add a book summary before analyzing');
   *   } else {
   *     console.error('Analysis failed:', error.message);
   *   }
   * }
   * ```
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
      headers: await this.getHeaders(),
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
   *
   * Uses AI to generate relevant questions that help refine the book's
   * table of contents structure. Questions are based on the book summary
   * and target audience.
   *
   * @param bookId - Unique identifier for the book
   * @returns Promise resolving to generated questions array
   *
   * @throws {Error} When generation fails
   *   - 400: Book has no summary or insufficient detail
   *   - 401: User is not authenticated
   *   - 403: User does not have access to this book
   *   - 404: Book not found
   *   - 500: Server error or AI service unavailable
   *
   * @example
   * ```typescript
   * const result = await bookClient.generateQuestions(bookId);
   * console.log(`Generated ${result.questions.length} questions`);
   * result.questions.forEach((q, i) => console.log(`${i + 1}. ${q}`));
   * ```
   */
  public async generateQuestions(bookId: string): Promise<{
    questions: string[];
  }> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}/generate-questions`, {
      method: 'POST',
      headers: await this.getHeaders(),
      credentials: 'include',
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to generate questions: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Generate table of contents from summary and question responses
   *
   * Uses AI to create a comprehensive table of contents based on the book summary
   * and user responses to clarifying questions. The generated TOC includes main chapters
   * and optional subchapters with descriptions and estimated page counts.
   *
   * @param bookId - Unique identifier for the book
   * @param questionResponses - Array of question/answer pairs from generateQuestions
   * @returns Promise resolving to generated TOC structure with success status
   *
   * @throws {Error} When generation fails
   *   - 400: Invalid request data or insufficient responses
   *   - 401: User is not authenticated
   *   - 403: User does not have access to this book
   *   - 404: Book not found
   *   - 422: Validation error (responses don't match questions)
   *   - 500: Server error or AI service unavailable
   *
   * @example
   * ```typescript
   * const responses = [
   *   { question: 'Target audience?', answer: 'Beginners' },
   *   { question: 'Key topics?', answer: 'Basics, Advanced, Tips' }
   * ];
   * const result = await bookClient.generateToc(bookId, responses);
   * if (result.success) {
   *   console.log(`Generated ${result.chapters_count} chapters`);
   *   await bookClient.updateToc(bookId, result.toc);
   * }
   * ```
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
      headers: await this.getHeaders(),
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
   * Get current table of contents for a book
   *
   * Retrieves the book's TOC structure including all chapters, subchapters, and metadata.
   * Returns null if no TOC has been generated yet.
   *
   * @param bookId - Unique identifier for the book
   * @returns Promise resolving to TOC structure or null if not generated
   *
   * @throws {Error} When retrieval fails
   *   - 401: User is not authenticated
   *   - 403: User does not have access to this book
   *   - 404: Book not found
   *   - 500: Server error occurred
   *
   * @example
   * ```typescript
   * const result = await bookClient.getToc(bookId);
   * if (result.toc === null) {
   *   console.log('No TOC generated yet');
   * } else {
   *   console.log(`TOC has ${result.toc.total_chapters} chapters`);
   * }
   * ```
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
      headers: await this.getHeaders(),
      credentials: 'include',
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to get TOC: ${response.status} ${error}`);
    }
    return response.json();
  }

  /**
   * Update table of contents for a book
   *
   * Replaces the entire TOC structure with provided data. This is a full replacement,
   * not a patch operation. Use after AI generation or manual TOC editing.
   *
   * @param bookId - Unique identifier for the book
   * @param toc - Complete TOC structure to save
   * @returns Promise resolving to updated TOC with success status
   *
   * @throws {Error} When update fails
   *   - 400: Invalid TOC structure
   *   - 401: User is not authenticated
   *   - 403: User does not have permission to edit this book
   *   - 404: Book not found
   *   - 422: Validation error (invalid chapter IDs, duplicate orders)
   *   - 500: Server error occurred
   *
   * @example
   * ```typescript
   * const generatedToc = await bookClient.generateToc(bookId, responses);
   * const result = await bookClient.updateToc(bookId, generatedToc.toc);
   * if (result.success) console.log('TOC saved successfully');
   * ```
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
      headers: await this.getHeaders(),
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
   *
   * Retrieves the current book summary along with optional revision history.
   * The summary is used for TOC generation and book planning.
   *
   * @param bookId - Unique identifier for the book
   * @returns Promise resolving to summary string and optional history array
   *
   * @throws {Error} When retrieval fails
   *   - 401: User is not authenticated
   *   - 403: User does not have access to this book
   *   - 404: Book not found
   *   - 500: Server error occurred
   *
   * @example
   * ```typescript
   * const result = await bookClient.getBookSummary(bookId);
   * console.log('Current summary:', result.summary);
   * if (result.summary_history) {
   *   console.log(`${result.summary_history.length} previous versions`);
   * }
   * ```
   */
  public async getBookSummary(bookId: string): Promise<{ summary: string; summary_history?: unknown[] }> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}/summary`, {
      headers: await this.getHeaders(),
      credentials: 'include',
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to fetch book summary: ${response.status} ${error}`);
    }
    return response.json();
  }
  /**
   * Save or update the summary for a book
   *
   * Updates the book's summary content. Previous versions are automatically saved
   * to revision history. The new summary becomes the active version.
   *
   * @param bookId - Unique identifier for the book
   * @param summary - New summary content (max 5000 characters)
   * @returns Promise resolving to saved summary and success status
   *
   * @throws {Error} When save fails
   *   - 400: Invalid request data
   *   - 401: User is not authenticated
   *   - 403: User does not have permission to edit this book
   *   - 404: Book not found
   *   - 422: Validation error (summary too long)
   *   - 500: Server error occurred
   *
   * @example
   * ```typescript
   * const summary = `This book explores...`;
   * const result = await bookClient.saveBookSummary(bookId, summary);
   * if (result.success) console.log('Summary saved');
   * ```
   */
  public async saveBookSummary(bookId: string, summary: string): Promise<{ summary: string; success: boolean }> {
    const response = await fetch(`${this.baseUrl}/books/${bookId}/summary`, {
      method: 'PUT',
      headers: await this.getHeaders(),
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
      headers: await this.getHeaders(),
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
      headers: await this.getHeaders(),
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
      headers: await this.getHeaders(),
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
      headers: await this.getHeaders(),
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
      headers: await this.getHeaders(),
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
      headers: await this.getHeaders(),
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
      headers: await this.getHeaders(),
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
      headers: await this.getHeaders(),
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
      headers: await this.getHeaders(),
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
        headers: await this.getHeaders(),
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
        headers: await this.getHeaders(),
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
        headers: await this.getHeaders(),
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
        headers: await this.getHeaders(),
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
        headers: await this.getHeaders(),
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
   * Save multiple question responses in a batch operation
   *
   * Efficiently saves multiple question responses in a single API call.
   * This method provides better performance and UX when saving many responses at once.
   *
   * @param bookId - Unique identifier for the book
   * @param chapterId - Unique identifier for the chapter
   * @param responses - Array of response objects to save
   * @returns Promise resolving to batch save results
   *
   * @throws {Error} When batch save fails
   *   - 400: Invalid request data or batch size exceeds limit (100 max)
   *   - 401: User is not authenticated
   *   - 403: User does not have permission to save responses for this book
   *   - 404: Book not found
   *   - 500: Server error occurred
   *
   * @example
   * ```typescript
   * const responses = [
   *   {
   *     question_id: 'q1',
   *     response_text: 'Answer to question 1',
   *     status: 'completed'
   *   },
   *   {
   *     question_id: 'q2',
   *     response_text: 'Draft answer to question 2',
   *     status: 'draft'
   *   }
   * ];
   *
   * const result = await bookClient.saveQuestionResponsesBatch(
   *   bookId,
   *   chapterId,
   *   responses
   * );
   *
   * console.log(`Saved ${result.saved}/${result.total} responses`);
   *
   * // Check for partial failures
   * if (result.failed > 0) {
   *   console.error('Failed responses:', result.errors);
   *   result.results.forEach(r => {
   *     if (!r.success) {
   *       console.error(`Question ${r.question_id}: ${r.error}`);
   *     }
   *   });
   * }
   * ```
   */
  public async saveQuestionResponsesBatch(
    bookId: string,
    chapterId: string,
    responses: Array<{
      question_id: string;
      response_text: string;
      status?: 'draft' | 'completed';
    }>
  ): Promise<{
    success: boolean;
    total: number;
    saved: number;
    failed: number;
    results: Array<{
      index: number;
      question_id: string;
      response_id?: string;
      success: boolean;
      is_update?: boolean;
      error?: string;
    }>;
    errors?: Array<{
      index: number;
      question_id?: string;
      error: string;
    }>;
    message: string;
  }> {
    const response = await fetch(
      `${this.baseUrl}/books/${bookId}/chapters/${chapterId}/questions/responses/batch`,
      {
        method: 'POST',
        headers: await this.getHeaders(),
        credentials: 'include',
        body: JSON.stringify(responses),
      }
    );
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to save question responses batch: ${response.status} ${error}`);
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
        headers: await this.getHeaders(),
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
        headers: await this.getHeaders(),
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
        headers: await this.getHeaders(),
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
        headers: await this.getHeaders(),
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
        headers: await this.getHeaders(),
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
      options?: Record<string, unknown>;
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
        headers: await this.getHeaders(),
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
        headers: await this.getHeaders(),
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
        headers: await this.getHeaders(),
        credentials: 'include',
      }
    );

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to delete chapter: ${response.status} ${error}`);
    }
  }

  // ============= AI Service Methods with Error Handling =============

  /**
   * Analyze summary with AI error handling and cached content support
   */
  public async analyzeSummaryWithErrorHandling(
    bookId: string,
    onRetry?: () => void | Promise<void>
  ): Promise<AIServiceResult<{
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
  }>> {
    try {
      const result = await this.analyzeSummary(bookId);
      return { data: result };
    } catch (error) {
      return handleAIServiceError(error, onRetry);
    }
  }

  /**
   * Generate questions with AI error handling and cached content support
   */
  public async generateQuestionsWithErrorHandling(
    bookId: string,
    onRetry?: () => void | Promise<void>
  ): Promise<AIServiceResult<{ questions: string[] }>> {
    try {
      const result = await this.generateQuestions(bookId);
      return { data: result };
    } catch (error) {
      return handleAIServiceError(error, onRetry);
    }
  }

  /**
   * Generate TOC with AI error handling and cached content support
   */
  public async generateTocWithErrorHandling(
    bookId: string,
    questionResponses: Array<{ question: string; answer: string }>,
    onRetry?: () => void | Promise<void>
  ): Promise<AIServiceResult<{
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
  }>> {
    try {
      const result = await this.generateToc(bookId, questionResponses);
      return { data: result };
    } catch (error) {
      return handleAIServiceError(error, onRetry);
    }
  }

  /**
   * Generate chapter questions with AI error handling and cached content support
   */
  public async generateChapterQuestionsWithErrorHandling(
    bookId: string,
    chapterId: string,
    options: GenerateQuestionsRequest = {},
    onRetry?: () => void | Promise<void>
  ): Promise<AIServiceResult<GenerateQuestionsResponse>> {
    try {
      const result = await this.generateChapterQuestions(bookId, chapterId, options);
      return { data: result };
    } catch (error) {
      return handleAIServiceError(error, onRetry);
    }
  }

  /**
   * Generate chapter draft with AI error handling and cached content support
   */
  public async generateChapterDraftWithErrorHandling(
    bookId: string,
    chapterId: string,
    data: {
      question_responses: Array<{ question: string; answer: string }>;
      writing_style?: string;
      target_length?: number;
    },
    onRetry?: () => void | Promise<void>
  ): Promise<AIServiceResult<{
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
  }>> {
    try {
      const result = await this.generateChapterDraft(bookId, chapterId, data);
      return { data: result };
    } catch (error) {
      return handleAIServiceError(error, onRetry);
    }
  }
}

// Create a singleton instance for use throughout the app
export const bookClient = new BookClient();

export default bookClient;
