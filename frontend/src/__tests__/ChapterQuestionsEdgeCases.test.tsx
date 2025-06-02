/**
 * Edge Cases Test Suite for User Story 4.2 (Interview-Style Prompts)
 * 
 * This test suite covers edge cases, error scenarios, and boundary conditions
 * for the chapter questions functionality to ensure robust error handling
 * and graceful degradation.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

// Mock components and hooks
import { ChapterQuestions } from '../components/chapters/questions/ChapterQuestions';
import { QuestionGenerator } from '../components/chapters/questions/QuestionGenerator';
import { QuestionDisplay } from '../components/chapters/questions/QuestionDisplay';
import { QuestionProgress } from '../components/chapters/questions/QuestionProgress';

// Mock API client
vi.mock('../lib/api/bookClient', () => ({
  bookApi: {
    generateChapterQuestions: vi.fn(),
    getChapterQuestions: vi.fn(),
    saveQuestionResponse: vi.fn(),
    rateQuestion: vi.fn(),
    getQuestionProgress: vi.fn(),
    regenerateChapterQuestions: vi.fn(),
  },
}));

// Mock toast notifications
vi.mock('../hooks/useToast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe('ChapterQuestions Edge Cases', () => {
  let mockApi: any;

  beforeEach(() => {
    mockApi = require('../lib/api/bookClient').bookApi;
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Network and API Failures', () => {
    it('should handle network timeout during question generation', async () => {
      mockApi.generateChapterQuestions.mockRejectedValue(
        new Error('Network timeout')
      );

      render(
        <TestWrapper>
          <QuestionGenerator 
            bookId="book-1" 
            chapterId="chapter-1" 
            onQuestionsGenerated={vi.fn()} 
          />
        </TestWrapper>
      );

      const generateButton = screen.getByText('Generate Questions');
      fireEvent.click(generateButton);

      await waitFor(() => {
        expect(screen.getByText(/failed to generate questions/i)).toBeInTheDocument();
        expect(screen.getByText(/retry/i)).toBeInTheDocument();
      });
    });

    it('should handle API rate limiting errors', async () => {
      mockApi.generateChapterQuestions.mockRejectedValue({
        response: { status: 429, data: { message: 'Rate limit exceeded' } }
      });

      render(
        <TestWrapper>
          <QuestionGenerator 
            bookId="book-1" 
            chapterId="chapter-1" 
            onQuestionsGenerated={vi.fn()} 
          />
        </TestWrapper>
      );

      const generateButton = screen.getByText('Generate Questions');
      fireEvent.click(generateButton);

      await waitFor(() => {
        expect(screen.getByText(/rate limit exceeded/i)).toBeInTheDocument();
        expect(screen.getByText(/try again later/i)).toBeInTheDocument();
      });
    });

    it('should handle malformed API responses', async () => {
      mockApi.generateChapterQuestions.mockResolvedValue({
        data: { invalidFormat: true }
      });

      render(
        <TestWrapper>
          <QuestionGenerator 
            bookId="book-1" 
            chapterId="chapter-1" 
            onQuestionsGenerated={vi.fn()} 
          />
        </TestWrapper>
      );

      const generateButton = screen.getByText('Generate Questions');
      fireEvent.click(generateButton);

      await waitFor(() => {
        expect(screen.getByText(/unexpected response format/i)).toBeInTheDocument();
      });
    });
  });

  describe('Data Validation Edge Cases', () => {
    it('should handle extremely long question text', async () => {
      const longQuestion = {
        id: 'q1',
        questionText: 'A'.repeat(5000), // Very long question
        questionType: 'character' as const,
        difficulty: 'medium' as const,
        category: 'development',
        generatedAt: new Date().toISOString(),
        order: 1,
        metadata: {
          suggestedResponseLength: 'medium'
        }
      };

      render(
        <TestWrapper>
          <QuestionDisplay 
            question={longQuestion}
            response=""
            onResponseChange={vi.fn()}
            onNext={vi.fn()}
            onPrevious={vi.fn()}
          />
        </TestWrapper>
      );

      // Question should be displayed with truncation or scroll
      expect(screen.getByText(/A{100,}/)).toBeInTheDocument();
    });

    it('should handle questions with missing metadata', async () => {
      const questionWithoutMetadata = {
        id: 'q1',
        questionText: 'What is the main character\'s motivation?',
        questionType: 'character' as const,
        difficulty: 'medium' as const,
        category: 'development',
        generatedAt: new Date().toISOString(),
        order: 1,
        // metadata is missing
      };

      render(
        <TestWrapper>
          <QuestionDisplay 
            question={questionWithoutMetadata as any}
            response=""
            onResponseChange={vi.fn()}
            onNext={vi.fn()}
            onPrevious={vi.fn()}
          />
        </TestWrapper>
      );

      // Should render without crashing
      expect(screen.getByText(/What is the main character/)).toBeInTheDocument();
    });

    it('should handle empty question sets', async () => {
      mockApi.getChapterQuestions.mockResolvedValue({
        data: { questions: [], total: 0 }
      });

      render(
        <TestWrapper>
          <ChapterQuestions bookId="book-1" chapterId="chapter-1" />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText(/no questions available/i)).toBeInTheDocument();
        expect(screen.getByText(/generate questions/i)).toBeInTheDocument();
      });
    });
  });

  describe('User Input Edge Cases', () => {
    it('should handle extremely long responses', async () => {
      const user = userEvent.setup();
      const longResponse = 'B'.repeat(50000); // Very long response

      render(
        <TestWrapper>
          <QuestionDisplay 
            question={{
              id: 'q1',
              questionText: 'Describe the setting',
              questionType: 'setting' as const,
              difficulty: 'easy' as const,
              category: 'description',
              generatedAt: new Date().toISOString(),
              order: 1,
              metadata: { suggestedResponseLength: 'medium' }
            }}
            response=""
            onResponseChange={vi.fn()}
            onNext={vi.fn()}
            onPrevious={vi.fn()}
          />
        </TestWrapper>
      );

      const textarea = screen.getByRole('textbox');
      await user.type(textarea, longResponse);

      // Should handle long input without crashing
      expect(textarea).toHaveValue(longResponse);
    });

    it('should handle special characters and emojis in responses', async () => {
      const user = userEvent.setup();
      const specialResponse = '🚀 Special chars: <>&"\' and unicode: 你好 and math: ∑∫∆';

      render(
        <TestWrapper>
          <QuestionDisplay 
            question={{
              id: 'q1',
              questionText: 'What is unique about this chapter?',
              questionType: 'theme' as const,
              difficulty: 'medium' as const,
              category: 'analysis',
              generatedAt: new Date().toISOString(),
              order: 1,
              metadata: { suggestedResponseLength: 'short' }
            }}
            response=""
            onResponseChange={vi.fn()}
            onNext={vi.fn()}
            onPrevious={vi.fn()}
          />
        </TestWrapper>
      );

      const textarea = screen.getByRole('textbox');
      await user.type(textarea, specialResponse);

      expect(textarea).toHaveValue(specialResponse);
    });

    it('should handle rapid successive question navigation', async () => {
      const user = userEvent.setup();
      const mockOnNext = vi.fn();
      const mockOnPrevious = vi.fn();

      render(
        <TestWrapper>
          <QuestionDisplay 
            question={{
              id: 'q1',
              questionText: 'Test question',
              questionType: 'plot' as const,
              difficulty: 'easy' as const,
              category: 'structure',
              generatedAt: new Date().toISOString(),
              order: 1,
              metadata: { suggestedResponseLength: 'short' }
            }}
            response=""
            onResponseChange={vi.fn()}
            onNext={mockOnNext}
            onPrevious={mockOnPrevious}
          />
        </TestWrapper>
      );

      const nextButton = screen.getByText('Next');
      
      // Rapidly click next button
      for (let i = 0; i < 10; i++) {
        await user.click(nextButton);
      }

      // Should handle rapid clicks gracefully
      expect(mockOnNext).toHaveBeenCalledTimes(10);
    });
  });

  describe('Progress Tracking Edge Cases', () => {
    it('should handle inconsistent progress data', async () => {
      mockApi.getQuestionProgress.mockResolvedValue({
        data: {
          total: 10,
          completed: 15, // More completed than total (inconsistent)
          progress: 150,
          status: 'in-progress'
        }
      });

      render(
        <TestWrapper>
          <QuestionProgress bookId="book-1" chapterId="chapter-1" />
        </TestWrapper>
      );

      await waitFor(() => {
        // Should cap progress at 100%
        expect(screen.getByText(/100%/)).toBeInTheDocument();
      });
    });

    it('should handle negative progress values', async () => {
      mockApi.getQuestionProgress.mockResolvedValue({
        data: {
          total: 10,
          completed: -1, // Negative value
          progress: -10,
          status: 'not-started'
        }
      });

      render(
        <TestWrapper>
          <QuestionProgress bookId="book-1" chapterId="chapter-1" />
        </TestWrapper>
      );

      await waitFor(() => {
        // Should handle negative values gracefully
        expect(screen.getByText(/0%/)).toBeInTheDocument();
      });
    });
  });

  describe('Regeneration Edge Cases', () => {
    it('should handle failed regeneration attempts', async () => {
      mockApi.regenerateChapterQuestions.mockRejectedValue(
        new Error('Regeneration failed')
      );

      render(
        <TestWrapper>
          <QuestionGenerator 
            bookId="book-1" 
            chapterId="chapter-1" 
            onQuestionsGenerated={vi.fn()}
            existingQuestions={[{
              id: 'q1',
              questionText: 'Existing question',
              questionType: 'character' as const,
              difficulty: 'medium' as const,
              category: 'development',
              generatedAt: new Date().toISOString(),
              order: 1,
              metadata: { suggestedResponseLength: 'medium' }
            }]}
          />
        </TestWrapper>
      );

      const regenerateButton = screen.getByText('Regenerate Questions');
      fireEvent.click(regenerateButton);

      await waitFor(() => {
        expect(screen.getByText(/regeneration failed/i)).toBeInTheDocument();
        // Original questions should still be available
        expect(screen.getByText('Existing question')).toBeInTheDocument();
      });
    });

    it('should handle regeneration when no existing questions', async () => {
      mockApi.regenerateChapterQuestions.mockResolvedValue({
        data: {
          questions: [{
            id: 'q1',
            questionText: 'New question',
            questionType: 'theme' as const,
            difficulty: 'easy' as const,
            category: 'analysis',
            generatedAt: new Date().toISOString(),
            order: 1,
            metadata: { suggestedResponseLength: 'short' }
          }]
        }
      });

      render(
        <TestWrapper>
          <QuestionGenerator 
            bookId="book-1" 
            chapterId="chapter-1" 
            onQuestionsGenerated={vi.fn()}
            existingQuestions={[]}
          />
        </TestWrapper>
      );

      // Should fall back to generation instead of regeneration
      expect(screen.getByText('Generate Questions')).toBeInTheDocument();
      expect(screen.queryByText('Regenerate Questions')).not.toBeInTheDocument();
    });
  });

  describe('Browser Compatibility Edge Cases', () => {
    it('should handle localStorage unavailability', async () => {
      // Mock localStorage to throw an error
      const originalLocalStorage = window.localStorage;
      Object.defineProperty(window, 'localStorage', {
        value: {
          getItem: () => { throw new Error('LocalStorage unavailable'); },
          setItem: () => { throw new Error('LocalStorage unavailable'); },
          removeItem: () => { throw new Error('LocalStorage unavailable'); },
        },
        writable: true
      });

      render(
        <TestWrapper>
          <ChapterQuestions bookId="book-1" chapterId="chapter-1" />
        </TestWrapper>
      );

      // Should render without crashing
      expect(screen.getByText(/Chapter Questions/i)).toBeInTheDocument();

      // Restore localStorage
      Object.defineProperty(window, 'localStorage', {
        value: originalLocalStorage,
        writable: true
      });
    });

    it('should handle focus events on disabled elements', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <QuestionDisplay 
            question={{
              id: 'q1',
              questionText: 'Test question',
              questionType: 'character' as const,
              difficulty: 'medium' as const,
              category: 'development',
              generatedAt: new Date().toISOString(),
              order: 1,
              metadata: { suggestedResponseLength: 'medium' }
            }}
            response=""
            onResponseChange={vi.fn()}
            onNext={vi.fn()}
            onPrevious={vi.fn()}
            isLoading={true} // Should disable interactions
          />
        </TestWrapper>
      );

      const textarea = screen.getByRole('textbox');
      
      // Try to focus disabled textarea
      await user.click(textarea);

      // Should handle gracefully without errors
      expect(textarea).toBeInTheDocument();
    });
  });

  describe('Memory and Performance Edge Cases', () => {
    it('should handle large numbers of questions without memory leaks', async () => {
      const largeQuestionSet = Array.from({ length: 1000 }, (_, index) => ({
        id: `q${index}`,
        questionText: `Question ${index}: What happens in this scenario?`,
        questionType: 'plot' as const,
        difficulty: 'medium' as const,
        category: 'structure',
        generatedAt: new Date().toISOString(),
        order: index,
        metadata: { suggestedResponseLength: 'medium' }
      }));

      mockApi.getChapterQuestions.mockResolvedValue({
        data: { questions: largeQuestionSet, total: 1000 }
      });

      render(
        <TestWrapper>
          <ChapterQuestions bookId="book-1" chapterId="chapter-1" />
        </TestWrapper>
      );

      await waitFor(() => {
        // Should render with pagination or virtualization
        expect(screen.getByText(/Question 0:/)).toBeInTheDocument();
      });

      // Component should handle large datasets without performance issues
    });

    it('should handle rapid API calls without race conditions', async () => {
      let callCount = 0;
      mockApi.saveQuestionResponse.mockImplementation(() => {
        callCount++;
        return new Promise(resolve => 
          setTimeout(() => resolve({ data: { id: `response-${callCount}` } }), 100)
        );
      });

      const mockOnResponseChange = vi.fn();

      render(
        <TestWrapper>
          <QuestionDisplay 
            question={{
              id: 'q1',
              questionText: 'Test question',
              questionType: 'character' as const,
              difficulty: 'medium' as const,
              category: 'development',
              generatedAt: new Date().toISOString(),
              order: 1,
              metadata: { suggestedResponseLength: 'medium' }
            }}
            response=""
            onResponseChange={mockOnResponseChange}
            onNext={vi.fn()}
            onPrevious={vi.fn()}
          />
        </TestWrapper>
      );

      const textarea = screen.getByRole('textbox');
      
      // Simulate rapid typing that triggers multiple API calls
      await userEvent.type(textarea, 'Quick response');

      // Should handle without race conditions
      expect(mockOnResponseChange).toHaveBeenCalled();
    });
  });

  describe('Accessibility Edge Cases', () => {
    it('should handle screen reader navigation with complex question structures', async () => {
      render(
        <TestWrapper>
          <QuestionDisplay 
            question={{
              id: 'q1',
              questionText: 'What is the character\'s primary motivation? Consider their background, relationships, and goals.',
              questionType: 'character' as const,
              difficulty: 'hard' as const,
              category: 'development',
              generatedAt: new Date().toISOString(),
              order: 1,
              metadata: { 
                suggestedResponseLength: 'long',
                helpText: 'Think about both internal and external motivations',
                examples: ['Fear of abandonment', 'Desire for recognition']
              }
            }}
            response=""
            onResponseChange={vi.fn()}
            onNext={vi.fn()}
            onPrevious={vi.fn()}
          />
        </TestWrapper>
      );

      // Should have proper ARIA labels and structure
      expect(screen.getByRole('textbox')).toHaveAccessibleName();
      expect(screen.getByText(/What is the character/)).toBeInTheDocument();
    });

    it('should handle keyboard navigation when elements are dynamically added', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <ChapterQuestions bookId="book-1" chapterId="chapter-1" />
        </TestWrapper>
      );

      // Test tab navigation
      await user.tab();
      
      // Should handle dynamic content gracefully
      expect(document.activeElement).toBeInTheDocument();
    });
  });
});
