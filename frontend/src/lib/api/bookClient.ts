'use client';

import { BookProject } from '@/components/BookCard';

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
}

// Create a singleton instance for use throughout the app
export const bookClient = new BookClient();

export default bookClient;
