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
      const networkError = new Error('Network error');
      (networkError as any).status = 0;

      (bookClient.saveQuestionResponse as jest.Mock).mockRejectedValue(networkError);

      render(<QuestionDisplay {...mockProps} />);

      const textarea = screen.getByLabelText(/your response/i);
      fireEvent.change(textarea, { target: { value: 'Test response' } });

      const saveButton = screen.getByText(/save draft/i);
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/check your connection/i)).toBeInTheDocument();
      });
    });

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
      const serverError = new Error('Internal server error');
      (serverError as any).status = 500;

      (bookClient.saveQuestionResponse as jest.Mock).mockRejectedValue(serverError);

      render(<QuestionDisplay {...mockProps} />);

      const textarea = screen.getByLabelText(/your response/i);
      fireEvent.change(textarea, { target: { value: 'Test response' } });

      const saveButton = screen.getByText(/save draft/i);
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/server error/i)).toBeInTheDocument();
      });
    });
  });

  describe('Complete response with error handling', () => {
    it('should handle completion errors with retry', async () => {
      (bookClient.saveQuestionResponse as jest.Mock)
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({});

      render(<QuestionDisplay {...mockProps} />);

      const textarea = screen.getByLabelText(/your response/i);
      fireEvent.change(textarea, { target: { value: 'Test response' } });

      const completeButton = screen.getByText(/complete response/i);
      fireEvent.click(completeButton);

      await waitFor(() => {
        expect(screen.getByText(/save failed/i)).toBeInTheDocument();
      });

      const retryButton = screen.getByText(/retry/i);
      fireEvent.click(retryButton);

      await waitFor(() => {
        expect(screen.getByText(/saved successfully/i)).toBeInTheDocument();
      });
    });

    it('should queue completion when offline', async () => {
      const useOnlineStatus = require('@/hooks/useOnlineStatus').useOnlineStatus;
      useOnlineStatus.mockReturnValue({ isOnline: false, wasOffline: false });

      render(<QuestionDisplay {...mockProps} />);

      const textarea = screen.getByLabelText(/your response/i);
      fireEvent.change(textarea, { target: { value: 'Test response' } });

      const completeButton = screen.getByText(/complete response/i);
      fireEvent.click(completeButton);

      await waitFor(() => {
        expect(screen.getByText(/queued for retry/i)).toBeInTheDocument();
      });

      expect(retryQueue.add).toHaveBeenCalled();
    });
  });
});
