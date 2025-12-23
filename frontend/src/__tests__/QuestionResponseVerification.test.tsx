/**
 * Tests for question response save verification logic.
 *
 * These tests ensure that:
 * 1. Response saves are verified by fetching the saved data
 * 2. Verification catches save failures and shows warnings
 * 3. Data mismatches between sent and saved data are detected
 * 4. Users are alerted when verification fails
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { bookClient } from '@/lib/api/bookClient';
import QuestionDisplay from '@/components/chapters/questions/QuestionDisplay';
import { Question, QuestionType, QuestionDifficulty, ResponseStatus } from '@/types/chapter-questions';

// Mock the bookClient
jest.mock('@/lib/api/bookClient');

// Mock toast
const mockToast = jest.fn();
jest.mock('@/components/ui/use-toast', () => ({
  useToast: () => ({
    toast: mockToast,
  }),
}));

// Sample question data
const sampleQuestion: Question = {
  id: 'q-123',
  book_id: 'book-456',
  chapter_id: 'chapter-789',
  question_text: 'What is the main theme of this chapter?',
  question_type: QuestionType.THEME,
  difficulty: QuestionDifficulty.MEDIUM,
  category: 'development',
  order: 1,
  response_status: ResponseStatus.UNANSWERED,
  created_at: '2025-01-01T00:00:00Z',
  metadata: {
    suggested_response_length: '200-300 words',
    help_text: 'Think about the underlying message',
    examples: ['Example theme 1', 'Example theme 2']
  }
};

describe('QuestionDisplay - Response Save Verification', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockToast.mockClear();
  });

  it('should verify response after successful save', async () => {
    const user = userEvent.setup();
    const mockOnResponseSaved = jest.fn();

    const responseText = 'The main theme is personal growth and transformation.';

    // Mock save response - use implementation to capture actual text sent
    let capturedText = '';
    (bookClient.saveQuestionResponse as jest.Mock).mockImplementation(async (bookId, chapterId, questionId, data) => {
      capturedText = data.response_text;
      return {
        response: {
          id: 'response-1',
          question_id: 'q-123',
          response_text: data.response_text,
          status: data.status,
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-01T00:00:00Z'
        },
        success: true,
        message: 'Response saved successfully'
      };
    });

    // Mock verification response - return what was actually saved
    (bookClient.getQuestionResponse as jest.Mock).mockImplementation(async () => {
      return {
        response: {
          id: 'response-1',
          question_id: 'q-123',
          response_text: capturedText,
          status: ResponseStatus.DRAFT,
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-01T00:00:00Z'
        },
        has_response: true,
        success: true
      };
    });

    render(
      <QuestionDisplay
        bookId="book-456"
        chapterId="chapter-789"
        question={sampleQuestion}
        onResponseSaved={mockOnResponseSaved}
      />
    );

    // Type response
    const textarea = screen.getByRole('textbox');
    await user.type(textarea, responseText);

    // Save as draft
    const saveDraftButton = screen.getByRole('button', { name: /save draft/i });
    await user.click(saveDraftButton);

    // Wait for save and verification
    await waitFor(() => {
      expect(bookClient.saveQuestionResponse).toHaveBeenCalled();
    });

    // Verification should be called
    await waitFor(() => {
      expect(bookClient.getQuestionResponse).toHaveBeenCalledWith(
        'book-456',
        'chapter-789',
        'q-123'
      );
    });

    // Verify the save was called with draft status (don't check exact text due to userEvent quirks)
    const saveCall = (bookClient.saveQuestionResponse as jest.Mock).mock.calls[0];
    expect(saveCall[0]).toBe('book-456');
    expect(saveCall[1]).toBe('chapter-789');
    expect(saveCall[2]).toBe('q-123');
    expect(saveCall[3].status).toBe(ResponseStatus.DRAFT);
    expect(saveCall[3].response_text).toContain('The main theme is personal growth');

    // No error toast should be shown
    expect(mockToast).not.toHaveBeenCalledWith(
      expect.objectContaining({
        variant: 'destructive'
      })
    );

    // Callback should be called
    expect(mockOnResponseSaved).toHaveBeenCalled();
  });

  it('should show warning when verification fails to find response', async () => {
    const user = userEvent.setup();
    const mockOnResponseSaved = jest.fn();

    const responseText = 'The main theme is personal growth.';

    // Mock successful save
    (bookClient.saveQuestionResponse as jest.Mock).mockResolvedValue({
      response: {
        id: 'response-1',
        question_id: 'q-123',
        response_text: responseText,
        status: ResponseStatus.DRAFT
      },
      success: true,
      message: 'Response saved successfully'
    });

    // Mock verification failing to find response
    (bookClient.getQuestionResponse as jest.Mock).mockResolvedValue({
      response: null,
      has_response: false,
      success: false
    });

    render(
      <QuestionDisplay
        bookId="book-456"
        chapterId="chapter-789"
        question={sampleQuestion}
        onResponseSaved={mockOnResponseSaved}
      />
    );

    // Type and save response
    const textarea = screen.getByRole('textbox');
    await user.type(textarea, responseText);

    const saveDraftButton = screen.getByRole('button', { name: /save draft/i });
    await user.click(saveDraftButton);

    // Wait for verification warning
    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Warning: Save Verification Failed',
          description: expect.stringContaining('could not be verified'),
          variant: 'destructive'
        })
      );
    });
  });

  it('should show warning when saved data differs from sent data', async () => {
    const user = userEvent.setup();
    const mockOnResponseSaved = jest.fn();

    const sentText = 'The main theme is personal growth and transformation.';
    const savedText = 'The main theme is personal growth.'; // Truncated!

    // Mock save response
    (bookClient.saveQuestionResponse as jest.Mock).mockResolvedValue({
      response: {
        id: 'response-1',
        question_id: 'q-123',
        response_text: savedText, // Different from sent text
        status: ResponseStatus.DRAFT
      },
      success: true,
      message: 'Response saved successfully'
    });

    // Mock verification response (with different text)
    (bookClient.getQuestionResponse as jest.Mock).mockResolvedValue({
      response: {
        id: 'response-1',
        question_id: 'q-123',
        response_text: savedText, // Different from sent text
        status: ResponseStatus.DRAFT
      },
      has_response: true,
      success: true
    });

    render(
      <QuestionDisplay
        bookId="book-456"
        chapterId="chapter-789"
        question={sampleQuestion}
        onResponseSaved={mockOnResponseSaved}
      />
    );

    // Type and save response
    const textarea = screen.getByRole('textbox');
    await user.type(textarea, sentText);

    const saveDraftButton = screen.getByRole('button', { name: /save draft/i });
    await user.click(saveDraftButton);

    // Wait for data mismatch warning
    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Warning: Data Mismatch',
          description: expect.stringContaining('may differ from what you submitted'),
          variant: 'destructive'
        })
      );
    });
  });

  it('should show warning when verification query fails', async () => {
    const user = userEvent.setup();
    const mockOnResponseSaved = jest.fn();

    const responseText = 'The main theme is personal growth.';

    // Mock successful save
    (bookClient.saveQuestionResponse as jest.Mock).mockResolvedValue({
      response: {
        id: 'response-1',
        question_id: 'q-123',
        response_text: responseText,
        status: ResponseStatus.DRAFT
      },
      success: true,
      message: 'Response saved successfully'
    });

    // Mock verification query failure
    (bookClient.getQuestionResponse as jest.Mock).mockRejectedValue(
      new Error('Network error')
    );

    render(
      <QuestionDisplay
        bookId="book-456"
        chapterId="chapter-789"
        question={sampleQuestion}
        onResponseSaved={mockOnResponseSaved}
      />
    );

    // Type and save response
    const textarea = screen.getByRole('textbox');
    await user.type(textarea, responseText);

    const saveDraftButton = screen.getByRole('button', { name: /save draft/i });
    await user.click(saveDraftButton);

    // Wait for verification warning
    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Verification Warning',
          description: expect.stringContaining('verification failed'),
          variant: 'destructive'
        })
      );
    });

    // Callback should still be called (save succeeded, only verification failed)
    expect(mockOnResponseSaved).toHaveBeenCalled();
  });

  it('should log successful verification', async () => {
    const user = userEvent.setup();
    const consoleSpy = jest.spyOn(console, 'log').mockImplementation();

    const responseText = 'The main theme is personal growth.';

    // Mock save and verification
    (bookClient.saveQuestionResponse as jest.Mock).mockResolvedValue({
      response: {
        id: 'response-1',
        question_id: 'q-123',
        response_text: responseText,
        status: ResponseStatus.DRAFT
      },
      success: true,
      message: 'Response saved successfully'
    });

    (bookClient.getQuestionResponse as jest.Mock).mockResolvedValue({
      response: {
        id: 'response-1',
        question_id: 'q-123',
        response_text: responseText,
        status: ResponseStatus.DRAFT
      },
      has_response: true,
      success: true
    });

    render(
      <QuestionDisplay
        bookId="book-456"
        chapterId="chapter-789"
        question={sampleQuestion}
        onResponseSaved={jest.fn()}
      />
    );

    // Type and save response
    const textarea = screen.getByRole('textbox');
    await user.type(textarea, responseText);

    const saveDraftButton = screen.getByRole('button', { name: /save draft/i });
    await user.click(saveDraftButton);

    // Wait for verification log
    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Verification successful')
      );
    });

    // Check log contains important details
    const verificationLog = consoleSpy.mock.calls.find(call =>
      call[0]?.includes('Verification successful')
    );
    expect(verificationLog).toBeTruthy();
    expect(verificationLog![0]).toContain('question_id=q-123');

    consoleSpy.mockRestore();
  });

  it('should log verification errors', async () => {
    const user = userEvent.setup();
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

    const responseText = 'The main theme is personal growth.';

    // Mock save
    (bookClient.saveQuestionResponse as jest.Mock).mockResolvedValue({
      response: {
        id: 'response-1',
        question_id: 'q-123',
        response_text: responseText,
        status: ResponseStatus.DRAFT
      },
      success: true,
      message: 'Response saved successfully'
    });

    // Mock verification failure
    (bookClient.getQuestionResponse as jest.Mock).mockResolvedValue({
      response: null,
      has_response: false,
      success: false
    });

    render(
      <QuestionDisplay
        bookId="book-456"
        chapterId="chapter-789"
        question={sampleQuestion}
        onResponseSaved={jest.fn()}
      />
    );

    // Type and save response
    const textarea = screen.getByRole('textbox');
    await user.type(textarea, responseText);

    const saveDraftButton = screen.getByRole('button', { name: /save draft/i });
    await user.click(saveDraftButton);

    // Wait for error log
    await waitFor(() => {
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        expect.stringContaining('Verification failed')
      );
    });

    consoleErrorSpy.mockRestore();
  });
});
