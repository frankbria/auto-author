/**
 * Tests for enhanced error handling in QuestionDisplay component
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import QuestionDisplay from '../QuestionDisplay';
import { Question, QuestionType, QuestionDifficulty, ResponseStatus } from '@/types/chapter-questions';
import { bookClient } from '@/lib/api/bookClient';
import { retryQueue } from '@/lib/utils/retryQueue';

// Mock dependencies
jest.mock('@/lib/api/bookClient');
jest.mock('@/lib/utils/retryQueue');
jest.mock('@/hooks/useOnlineStatus', () => ({
  useOnlineStatus: jest.fn(() => ({ isOnline: true, wasOffline: false })),
}));

// Mock toast
const mockToast = jest.fn();
jest.mock('@/components/ui/use-toast', () => ({
  useToast: () => ({
    toast: mockToast,
  }),
}));

const mockQuestion: Question = {
  id: 'question-1',
  book_id: 'book-1',
  chapter_id: 'chapter-1',
  question_type: QuestionType.CHARACTER,
  difficulty: QuestionDifficulty.MEDIUM,
  question_text: 'Describe the main character',
  metadata: {
    help_text: 'Think about personality traits',
    examples: ['Brave', 'Thoughtful'],
    suggested_response_length: '100-200 words',
  },
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const mockProps = {
  bookId: 'book-1',
  chapterId: 'chapter-1',
  question: mockQuestion,
  onResponseSaved: jest.fn(),
  onRegenerateQuestion: jest.fn(),
};

describe('QuestionDisplay - Enhanced Error Handling', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockToast.mockClear();

    // Use real timers for each test
    jest.useRealTimers();

    // Reset useOnlineStatus to default online state
    const useOnlineStatus = require('@/hooks/useOnlineStatus').useOnlineStatus;
    useOnlineStatus.mockReturnValue({ isOnline: true, wasOffline: false });

    // Mock getQuestionResponse to prevent verification errors
    (bookClient.getQuestionResponse as jest.Mock).mockResolvedValue({
      has_response: false,
      response: null,
      success: false
    });
  });

  describe('Save operation with retry logic', () => {
    it('should show saving status indicator', async () => {
      (bookClient.saveQuestionResponse as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(resolve, 100))
      );

      render(<QuestionDisplay {...mockProps} />);

      const textarea = screen.getByLabelText(/your response/i);
      fireEvent.change(textarea, { target: { value: 'Test response' } });

      const saveButton = screen.getByText(/save draft/i);
      fireEvent.click(saveButton);

      expect(screen.getByText(/saving/i)).toBeInTheDocument();
    });

    it('should show saved status after successful save', async () => {
      (bookClient.saveQuestionResponse as jest.Mock).mockResolvedValue({});

      render(<QuestionDisplay {...mockProps} />);

      const textarea = screen.getByLabelText(/your response/i);
      fireEvent.change(textarea, { target: { value: 'Test response' } });

      const saveButton = screen.getByText(/save draft/i);
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/saved successfully/i)).toBeInTheDocument();
      });

      expect(mockProps.onResponseSaved).toHaveBeenCalled();
    });

    it('should show error status with retry button on failure', async () => {
      (bookClient.saveQuestionResponse as jest.Mock).mockRejectedValue(
        new Error('Network error')
      );

      render(<QuestionDisplay {...mockProps} />);

      const textarea = screen.getByLabelText(/your response/i);
      fireEvent.change(textarea, { target: { value: 'Test response' } });

      const saveButton = screen.getByText(/save draft/i);
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/save failed/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/retry/i)).toBeInTheDocument();
    });

    it('should retry save operation when retry button is clicked', async () => {
      (bookClient.saveQuestionResponse as jest.Mock)
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({});

      render(<QuestionDisplay {...mockProps} />);

      const textarea = screen.getByLabelText(/your response/i);
      fireEvent.change(textarea, { target: { value: 'Test response' } });

      const saveButton = screen.getByText(/save draft/i);
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/save failed/i)).toBeInTheDocument();
      });

      const retryButton = screen.getByText(/retry/i);
      fireEvent.click(retryButton);

      await waitFor(() => {
        expect(screen.getByText(/saved successfully/i)).toBeInTheDocument();
      });

      expect(bookClient.saveQuestionResponse).toHaveBeenCalledTimes(2);
    });
  });

  describe('Offline handling', () => {
    it('should queue save when offline', async () => {
      const useOnlineStatus = require('@/hooks/useOnlineStatus').useOnlineStatus;
      useOnlineStatus.mockReturnValue({ isOnline: false, wasOffline: false });

      render(<QuestionDisplay {...mockProps} />);

      const textarea = screen.getByLabelText(/your response/i);
      fireEvent.change(textarea, { target: { value: 'Test response' } });

      const saveButton = screen.getByText(/save draft/i);
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/queued for retry/i)).toBeInTheDocument();
      });

      expect(retryQueue.add).toHaveBeenCalled();
    });

    it('should show offline mode indicator', () => {
      const useOnlineStatus = require('@/hooks/useOnlineStatus').useOnlineStatus;
      useOnlineStatus.mockReturnValue({ isOnline: false, wasOffline: false });

      render(<QuestionDisplay {...mockProps} />);

      expect(screen.getByText(/offline mode/i)).toBeInTheDocument();
    });

    it('should show connection restored notification', () => {
      const useOnlineStatus = require('@/hooks/useOnlineStatus').useOnlineStatus;
      useOnlineStatus.mockReturnValue({ isOnline: true, wasOffline: true });

      render(<QuestionDisplay {...mockProps} />);

      expect(screen.getByText(/connection restored/i)).toBeInTheDocument();
    });
  });

  describe('Error messages', () => {
    it('should show network error message with actionable suggestion', async () => {
      // Create error with name property explicitly set
      const networkError = new Error('Network error');
      Object.defineProperty(networkError, 'name', {
        value: 'NetworkError',
        writable: false,
        enumerable: false,
        configurable: true
      });

      // Mock all 3 internal ErrorHandler attempts to fail
      (bookClient.saveQuestionResponse as jest.Mock)
        .mockRejectedValueOnce(networkError)
        .mockRejectedValueOnce(networkError)
        .mockRejectedValueOnce(networkError);

      render(<QuestionDisplay {...mockProps} />);

      const textarea = screen.getByLabelText(/your response/i);
      fireEvent.change(textarea, { target: { value: 'Test response' } });

      const saveButton = screen.getByText(/save draft/i);
      fireEvent.click(saveButton);

      // ErrorHandler retries internally with backoff 1s + 2s + 4s ≈ 7s before throwing
      await waitFor(() => {
        expect(screen.getByText(/check your connection/i)).toBeInTheDocument();
      }, { timeout: 10000 });
    }, 15000);

    it('should show authentication error message', async () => {
      const authError = new Error('Unauthorized');
      (authError as any).status = 401;

      (bookClient.saveQuestionResponse as jest.Mock).mockRejectedValue(authError);

      render(<QuestionDisplay {...mockProps} />);

      const textarea = screen.getByLabelText(/your response/i);
      fireEvent.change(textarea, { target: { value: 'Test response' } });

      const saveButton = screen.getByText(/save draft/i);
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/sign in again/i)).toBeInTheDocument();
      });
    });

    it('should show server error message', async () => {
      // Create error with status property for server error classification
      const serverError = new Error('Internal server error') as Error & { status: number };
      serverError.status = 500;

      (bookClient.saveQuestionResponse as jest.Mock).mockRejectedValue(serverError);

      render(<QuestionDisplay {...mockProps} />);

      const textarea = screen.getByLabelText(/your response/i);
      fireEvent.change(textarea, { target: { value: 'Test response' } });

      const saveButton = screen.getByText(/save draft/i);
      fireEvent.click(saveButton);

      // ErrorHandler retries server errors internally with backoff 1s + 2s + 4s ≈ 7s
      await waitFor(() => {
        expect(screen.getByText(/server error/i)).toBeInTheDocument();
      }, { timeout: 10000 });
    }, 15000);
  });

  describe('Auto-save suppression after failed save (#197)', () => {
    it('does not auto-save again after a failed save; error persists until the user acts', async () => {
      // Plain Error classifies as UNKNOWN → not retryable → fails on the first attempt
      (bookClient.saveQuestionResponse as jest.Mock).mockRejectedValue(new Error('boom'));

      render(<QuestionDisplay {...mockProps} />);

      const textarea = screen.getByLabelText(/your response/i);
      fireEvent.change(textarea, { target: { value: 'Test response' } });

      const saveButton = screen.getByText(/save draft/i);
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/save failed/i)).toBeInTheDocument();
      });
      expect(bookClient.saveQuestionResponse).toHaveBeenCalledTimes(1);

      // Sit past the 3s auto-save debounce — no further save may fire
      await new Promise(resolve => setTimeout(resolve, 3500));

      expect(bookClient.saveQuestionResponse).toHaveBeenCalledTimes(1);
      expect(screen.getByText(/save failed/i)).toBeInTheDocument();
      expect(screen.getByText(/failed to save draft/i)).toBeInTheDocument();
    }, 10000);

    it('clears the error when the user edits, and auto-save resumes', async () => {
      (bookClient.saveQuestionResponse as jest.Mock)
        .mockRejectedValueOnce(new Error('boom'))
        .mockResolvedValue({});

      render(<QuestionDisplay {...mockProps} />);

      const textarea = screen.getByLabelText(/your response/i);
      fireEvent.change(textarea, { target: { value: 'Test response' } });

      const saveButton = screen.getByText(/save draft/i);
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/save failed/i)).toBeInTheDocument();
      });

      // Typing is the user acting on the error: banner clears immediately
      fireEvent.change(textarea, { target: { value: 'Test response, edited' } });

      expect(screen.queryByText(/save failed/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/failed to save draft/i)).not.toBeInTheDocument();

      // ...and the 3s auto-save debounce re-arms and saves the new text
      await waitFor(() => {
        expect(screen.getByText(/saved successfully/i)).toBeInTheDocument();
      }, { timeout: 6000 });
      expect(bookClient.saveQuestionResponse).toHaveBeenCalledTimes(2);
      expect((bookClient.saveQuestionResponse as jest.Mock).mock.calls[1][3]).toMatchObject({
        response_text: 'Test response, edited',
      });
    }, 10000);

    it('does not let a stale saved→idle timer clear a later error state', async () => {
      // First save succeeds (arming the 3s "clear saved status" timer),
      // the second save fails before that timer fires
      (bookClient.saveQuestionResponse as jest.Mock)
        .mockResolvedValueOnce({})
        .mockRejectedValue(new Error('boom'));

      render(<QuestionDisplay {...mockProps} />);

      const textarea = screen.getByLabelText(/your response/i);
      fireEvent.change(textarea, { target: { value: 'Test response' } });

      const saveButton = screen.getByText(/save draft/i);
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/saved successfully/i)).toBeInTheDocument();
      });

      fireEvent.change(textarea, { target: { value: 'Test response, edited' } });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/save failed/i)).toBeInTheDocument();
      });
      const callsAfterFailure = (bookClient.saveQuestionResponse as jest.Mock).mock.calls.length;

      // Sit past the first save's 3s saved→idle timer: it must not flip the
      // error state back to idle (which would re-arm auto-save)
      await new Promise(resolve => setTimeout(resolve, 3500));

      expect(screen.getByText(/save failed/i)).toBeInTheDocument();
      expect(bookClient.saveQuestionResponse).toHaveBeenCalledTimes(callsAfterFailure);
    }, 12000);

    it('resets the retry allowance when the user edits after exhausting retries', async () => {
      (bookClient.saveQuestionResponse as jest.Mock).mockRejectedValue(new Error('boom'));

      render(<QuestionDisplay {...mockProps} />);

      const textarea = screen.getByLabelText(/your response/i);
      fireEvent.change(textarea, { target: { value: 'Test response' } });

      fireEvent.click(screen.getByText(/save draft/i));
      await waitFor(() => expect(screen.getByText(/retry/i)).toBeInTheDocument());

      // Burn through the manual retry allowance (retryCount reaches 3)
      fireEvent.click(screen.getByText(/retry/i));
      await waitFor(() => expect(screen.getByText(/retry/i)).toBeInTheDocument());
      fireEvent.click(screen.getByText(/retry/i));
      // Wait for the settled error state: banner back, retry allowance exhausted
      await waitFor(() => {
        expect(screen.getByText(/failed to save draft/i)).toBeInTheDocument();
        expect(screen.queryByText(/retry/i)).not.toBeInTheDocument();
      });

      // Editing starts a fresh attempt cycle; when the resumed auto-save
      // fails again the Retry button must be offered again
      fireEvent.change(textarea, { target: { value: 'Test response, edited' } });

      await waitFor(() => {
        expect(screen.getByText(/save failed/i)).toBeInTheDocument();
        expect(screen.getByText(/retry/i)).toBeInTheDocument();
      }, { timeout: 6000 });
    }, 12000);
  });

  describe('Complete response with error handling', () => {
    it('should handle completion errors with retry', async () => {
      // Create error with name property explicitly set
      const networkError = new Error('Network error');
      Object.defineProperty(networkError, 'name', {
        value: 'NetworkError',
        writable: false,
        enumerable: false,
        configurable: true
      });

      // Fail all 3 internal ErrorHandler attempts so the error surfaces,
      // then succeed on the manual Retry click (a fresh execute call)
      (bookClient.saveQuestionResponse as jest.Mock)
        .mockRejectedValueOnce(networkError)
        .mockRejectedValueOnce(networkError)
        .mockRejectedValueOnce(networkError)
        .mockResolvedValueOnce({});

      render(<QuestionDisplay {...mockProps} />);

      const textarea = screen.getByLabelText(/your response/i);
      fireEvent.change(textarea, { target: { value: 'Test response' } });

      const completeButton = screen.getByRole('button', { name: /complete response/i });
      fireEvent.click(completeButton);

      // ErrorHandler retries internally with backoff 1s + 2s + 4s ≈ 7s before throwing
      await waitFor(() => {
        expect(screen.getByText(/check your connection/i)).toBeInTheDocument();
      }, { timeout: 10000 });

      const retryButton = screen.getByText(/retry/i);
      fireEvent.click(retryButton);

      // Manual retry succeeds (mockResolvedValueOnce)
      await waitFor(() => {
        expect(screen.getByText(/saved successfully/i)).toBeInTheDocument();
      }, { timeout: 5000 });
    }, 20000);

    it('should queue completion when offline', async () => {
      const useOnlineStatus = require('@/hooks/useOnlineStatus').useOnlineStatus;
      useOnlineStatus.mockReturnValue({ isOnline: false, wasOffline: false });

      render(<QuestionDisplay {...mockProps} />);

      const textarea = screen.getByLabelText(/your response/i);
      fireEvent.change(textarea, { target: { value: 'Test response' } });

      const completeButton = screen.getByRole('button', { name: /complete response/i });
      fireEvent.click(completeButton);

      await waitFor(() => {
        expect(screen.getByText(/queued for retry/i)).toBeInTheDocument();
      });

      expect(retryQueue.add).toHaveBeenCalled();
    });
  });
});
