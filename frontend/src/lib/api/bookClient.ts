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
}

// Create a singleton instance for use throughout the app
export const bookClient = new BookClient();

export default bookClient;
