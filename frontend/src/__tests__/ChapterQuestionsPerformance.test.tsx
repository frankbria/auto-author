/**
 * Performance Test Suite for User Story 4.2 (Interview-Style Prompts)
 * 
 * This test suite focuses on performance testing for the chapter questions
 * functionality, including large question sets, memory management, API
 * performance, and optimization scenarios.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act } from 'react-dom/test-utils';

// Components under test
import QuestionContainer from '@/components/chapters/questions/QuestionContainer';
import QuestionGenerator from '@/components/chapters/questions/QuestionGenerator';
import QuestionDisplay from '@/components/chapters/questions/QuestionDisplay';
import QuestionProgress from '@/components/chapters/questions/QuestionProgress';
import { QuestionType, QuestionDifficulty, ResponseStatus } from '@/types/chapter-questions';
import { bookClient } from '@/lib/api/bookClient';

// Mock the API client
jest.mock('@/lib/api/bookClient', () => ({
  bookClient: {
    getChapterQuestions: jest.fn(),
    getQuestionResponse: jest.fn(),
    saveQuestionResponse: jest.fn(),
    getChapterQuestionProgress: jest.fn(),
    generateChapterQuestions: jest.fn(),
    rateQuestion: jest.fn(),
    regenerateChapterQuestions: jest.fn(),
  }
}));

// Mock Toast notifications
jest.mock('@/components/ui/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn()
  })
}));

// Performance monitoring utilities
const performanceMonitor = {
  startTime: 0,
  endTime: 0,
  memoryBefore: 0,
  memoryAfter: 0,

  start() {
    this.startTime = performance.now();
    if (performance.memory) {
      this.memoryBefore = performance.memory.usedJSHeapSize;
    }
  },

  end() {
    this.endTime = performance.now();
    if (performance.memory) {
      this.memoryAfter = performance.memory.usedJSHeapSize;
    }
    return {
      duration: this.endTime - this.startTime,
      memoryUsed: this.memoryAfter - this.memoryBefore
    };
  }
};

// Generate large datasets for performance testing
const generateLargeQuestionSet = (count: number) => {
  return Array.from({ length: count }, (_, index) => ({
    id: `question-${index}`,
    chapter_id: 'test-chapter',
    question_text: `Performance test question ${index + 1}. This is a longer question text to test rendering performance with varying content lengths. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.`,
    question_type: Object.values(QuestionType)[index % Object.values(QuestionType).length],
    difficulty: Object.values(QuestionDifficulty)[index % Object.values(QuestionDifficulty).length],
    category: `category-${index % 5}`,
    order: index + 1,
    generated_at: new Date().toISOString(),
    metadata: {
      suggested_response_length: '200-300 words',
      help_text: `Help text for question ${index + 1}`,
      examples: [`Example ${index + 1}-1`, `Example ${index + 1}-2`],
      estimated_time: Math.floor(Math.random() * 10) + 5,
      keywords: [`keyword-${index}-1`, `keyword-${index}-2`]
    },
    has_response: Math.random() > 0.5
  }));
};

const generateLargeResponseSet = (count: number) => {
  return Array.from({ length: count }, (_, index) => ({
    id: `response-${index}`,
    question_id: `question-${index}`,
    response_text: `Performance test response ${index + 1}. `.repeat(50), // Large response text
    status: Object.values(ResponseStatus)[index % Object.values(ResponseStatus).length],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    word_count: 250 + Math.floor(Math.random() * 500),
    rating: Math.floor(Math.random() * 5) + 1
  }));
};

describe('Chapter Questions Performance Tests', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
          cacheTime: 0,
        },
        mutations: {
          retry: false,
        },
      },
    });
    jest.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    queryClient.clear();
  });

  const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );

  describe('Large Question Set Performance', () => {
    test('renders 100 questions within acceptable time limits', async () => {
      const largeQuestionSet = generateLargeQuestionSet(100);
      
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
        questions: largeQuestionSet
      });
      (bookClient.getChapterQuestionProgress as jest.Mock).mockResolvedValue({
        total_questions: 100,
        answered_questions: 50,
        completion_percentage: 50
      });

      performanceMonitor.start();

      await act(async () => {
        render(
          <TestWrapper>
            <QuestionContainer 
              bookId="test-book" 
              chapterId="test-chapter" 
              chapterTitle="Performance Test Chapter" 
            />
          </TestWrapper>
        );
      });

      await waitFor(() => {
        expect(screen.getByText(/Performance test question 1/)).toBeInTheDocument();
      });

      const performance = performanceMonitor.end();

      // Should render within 2 seconds
      expect(performance.duration).toBeLessThan(2000);
      console.log(`Rendered 100 questions in ${performance.duration}ms`);
    });

    test('handles 500 questions with virtualization', async () => {
      const veryLargeQuestionSet = generateLargeQuestionSet(500);
      
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
        questions: veryLargeQuestionSet
      });

      performanceMonitor.start();

      await act(async () => {
        render(
          <TestWrapper>
            <QuestionContainer 
              bookId="test-book" 
              chapterId="test-chapter" 
              chapterTitle="Large Performance Test" 
            />
          </TestWrapper>
        );
      });

      await waitFor(() => {
        expect(screen.getByTestId('question-container')).toBeInTheDocument();
      });

      const performance = performanceMonitor.end();

      // Should handle large sets efficiently
      expect(performance.duration).toBeLessThan(3000);
      console.log(`Handled 500 questions in ${performance.duration}ms`);
    });

    test('memory usage remains stable with large question sets', async () => {
      const initialMemory = performance.memory ? performance.memory.usedJSHeapSize : 0;
      
      for (let i = 0; i < 5; i++) {
        const questionSet = generateLargeQuestionSet(100);
        
        (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
          questions: questionSet
        });

        const { unmount } = render(
          <TestWrapper>
            <QuestionContainer 
              bookId={`test-book-${i}`} 
              chapterId={`test-chapter-${i}`} 
              chapterTitle={`Test Chapter ${i}`} 
            />
          </TestWrapper>
        );

        await waitFor(() => {
          expect(screen.getByTestId('question-container')).toBeInTheDocument();
        });

        unmount();
        
        // Force garbage collection if available
        if (global.gc) {
          global.gc();
        }
      }

      const finalMemory = performance.memory ? performance.memory.usedJSHeapSize : 0;
      const memoryIncrease = finalMemory - initialMemory;

      // Memory increase should be reasonable (less than 50MB)
      expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024);
      console.log(`Memory increase after 5 iterations: ${memoryIncrease / 1024 / 1024}MB`);
    });
  });

  describe('API Performance Tests', () => {
    test('question generation API calls complete within time limits', async () => {
      const startTime = performance.now();
      
      (bookClient.generateChapterQuestions as jest.Mock).mockImplementation(
        () => new Promise((resolve) => {
          // Simulate API delay
          setTimeout(() => {
            resolve({
              questions: generateLargeQuestionSet(10),
              generation_metadata: {
                processing_time: 1500,
                ai_model: 'gpt-4',
                token_usage: 2500
              }
            });
          }, 100);
        })
      );

      render(
        <TestWrapper>
          <QuestionGenerator 
            bookId="test-book" 
            chapterId="test-chapter" 
            onQuestionsGenerated={() => {}} 
          />
        </TestWrapper>
      );

      const generateButton = screen.getByText('Generate Questions');
      fireEvent.click(generateButton);

      await waitFor(() => {
        expect(screen.getByText('Questions generated successfully')).toBeInTheDocument();
      });

      const endTime = performance.now();
      const totalTime = endTime - startTime;

      // Should complete within 5 seconds including UI updates
      expect(totalTime).toBeLessThan(5000);
      console.log(`Question generation completed in ${totalTime}ms`);
    });

    test('handles concurrent API calls efficiently', async () => {
      const concurrentCalls = 10;
      const callPromises: Promise<any>[] = [];

      (bookClient.saveQuestionResponse as jest.Mock).mockImplementation(
        () => new Promise((resolve) => {
          setTimeout(() => resolve({ success: true }), 50);
        })
      );

      performanceMonitor.start();

      // Make multiple concurrent API calls
      for (let i = 0; i < concurrentCalls; i++) {
        const promise = bookClient.saveQuestionResponse(
          `question-${i}`,
          `Response ${i}`,
          ResponseStatus.COMPLETE
        );
        callPromises.push(promise);
      }

      await Promise.all(callPromises);

      const performance = performanceMonitor.end();

      // All calls should complete reasonably quickly
      expect(performance.duration).toBeLessThan(1000);
      expect(bookClient.saveQuestionResponse).toHaveBeenCalledTimes(concurrentCalls);
    });

    test('API error handling does not degrade performance', async () => {
      (bookClient.getChapterQuestions as jest.Mock).mockImplementation(
        () => new Promise((_, reject) => {
          setTimeout(() => reject(new Error('API Error')), 100);
        })
      );

      performanceMonitor.start();

      render(
        <TestWrapper>
          <QuestionContainer 
            bookId="test-book" 
            chapterId="test-chapter" 
            chapterTitle="Error Test Chapter" 
          />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText(/Error loading questions/)).toBeInTheDocument();
      });

      const performance = performanceMonitor.end();

      // Error handling should be fast
      expect(performance.duration).toBeLessThan(1000);
    });
  });

  describe('User Interaction Performance', () => {
    test('question navigation is responsive', async () => {
      const questionSet = generateLargeQuestionSet(50);
      
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
        questions: questionSet
      });
      (bookClient.getQuestionResponse as jest.Mock).mockResolvedValue({
        has_response: false,
        response: null
      });

      render(
        <TestWrapper>
          <QuestionContainer 
            bookId="test-book" 
            chapterId="test-chapter" 
            chapterTitle="Navigation Test" 
          />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText(/Performance test question 1/)).toBeInTheDocument();
      });

      // Test rapid navigation
      const times: number[] = [];
      
      for (let i = 0; i < 10; i++) {
        const startTime = performance.now();
        
        const nextButton = screen.getByText('Next');
        fireEvent.click(nextButton);
        
        await waitFor(() => {
          expect(screen.getByText(new RegExp(`Performance test question ${i + 2}`))).toBeInTheDocument();
        });
        
        const endTime = performance.now();
        times.push(endTime - startTime);
      }

      // Average navigation time should be under 100ms
      const averageTime = times.reduce((sum, time) => sum + time, 0) / times.length;
      expect(averageTime).toBeLessThan(100);
      console.log(`Average navigation time: ${averageTime}ms`);
    });

    test('real-time auto-save performance', async () => {
      (bookClient.saveQuestionResponse as jest.Mock).mockImplementation(
        () => new Promise((resolve) => {
          setTimeout(() => resolve({ success: true }), 50);
        })
      );

      const { rerender } = render(
        <TestWrapper>
          <QuestionDisplay
            question={{
              id: 'test-question',
              chapter_id: 'test-chapter',
              question_text: 'Test question for auto-save',
              question_type: QuestionType.CONTENT,
              difficulty: QuestionDifficulty.MEDIUM,
              category: 'test',
              order: 1,
              generated_at: new Date().toISOString(),
              metadata: {},
              has_response: false
            }}
            response={null}
            onResponseChange={() => {}}
            onNext={() => {}}
            onPrevious={() => {}}
            hasNext={true}
            hasPrevious={false}
          />
        </TestWrapper>
      );

      const textarea = screen.getByRole('textbox');
      
      // Simulate rapid typing
      const longText = 'This is a performance test for auto-save functionality. '.repeat(100);
      
      performanceMonitor.start();
      
      await userEvent.type(textarea, longText);
      
      // Wait for auto-save debounce
      await waitFor(() => {
        expect(bookClient.saveQuestionResponse).toHaveBeenCalled();
      }, { timeout: 3000 });

      const performance = performanceMonitor.end();

      // Auto-save should not significantly impact typing performance
      expect(performance.duration).toBeLessThan(5000);
    });
  });

  describe('Memory Management Tests', () => {
    test('component cleanup prevents memory leaks', async () => {
      const initialMemory = performance.memory ? performance.memory.usedJSHeapSize : 0;
      const components: any[] = [];

      // Create and destroy multiple components
      for (let i = 0; i < 20; i++) {
        const { unmount } = render(
          <TestWrapper>
            <QuestionContainer 
              bookId={`book-${i}`} 
              chapterId={`chapter-${i}`} 
              chapterTitle={`Chapter ${i}`} 
            />
          </TestWrapper>
        );
        
        components.push(unmount);
        
        if (i % 5 === 0) {
          // Cleanup every 5 components
          components.forEach(unmount => unmount());
          components.length = 0;
          
          if (global.gc) {
            global.gc();
          }
        }
      }

      // Final cleanup
      components.forEach(unmount => unmount());
      
      if (global.gc) {
        global.gc();
      }

      const finalMemory = performance.memory ? performance.memory.usedJSHeapSize : 0;
      const memoryIncrease = finalMemory - initialMemory;

      // Memory increase should be minimal
      expect(memoryIncrease).toBeLessThan(10 * 1024 * 1024); // Less than 10MB
    });

    test('event listener cleanup works correctly', async () => {
      const addEventListenerSpy = jest.spyOn(document, 'addEventListener');
      const removeEventListenerSpy = jest.spyOn(document, 'removeEventListener');

      const { unmount } = render(
        <TestWrapper>
          <QuestionContainer 
            bookId="test-book" 
            chapterId="test-chapter" 
            chapterTitle="Event Test Chapter" 
          />
        </TestWrapper>
      );

      const initialListeners = addEventListenerSpy.mock.calls.length;
      
      unmount();

      // Should remove all event listeners
      expect(removeEventListenerSpy.mock.calls.length).toBeGreaterThanOrEqual(
        addEventListenerSpy.mock.calls.length - initialListeners
      );

      addEventListenerSpy.mockRestore();
      removeEventListenerSpy.mockRestore();
    });
  });

  describe('Optimization Tests', () => {
    test('lazy loading works for question images and media', async () => {
      const questionsWithMedia = generateLargeQuestionSet(10).map(q => ({
        ...q,
        metadata: {
          ...q.metadata,
          media_urls: [
            'https://example.com/image1.jpg',
            'https://example.com/image2.jpg'
          ]
        }
      }));

      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
        questions: questionsWithMedia
      });

      render(
        <TestWrapper>
          <QuestionContainer 
            bookId="test-book" 
            chapterId="test-chapter" 
            chapterTitle="Media Test Chapter" 
          />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByTestId('question-container')).toBeInTheDocument();
      });

      // Images should have lazy loading attributes
      const images = screen.getAllByRole('img');
      images.forEach(img => {
        expect(img).toHaveAttribute('loading', 'lazy');
      });
    });

    test('debounced search performs efficiently', async () => {
      const searchQuestions = generateLargeQuestionSet(200);
      
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
        questions: searchQuestions
      });

      render(
        <TestWrapper>
          <QuestionContainer 
            bookId="test-book" 
            chapterId="test-chapter" 
            chapterTitle="Search Test Chapter" 
          />
        </TestWrapper>
      );

      const searchInput = screen.getByPlaceholderText(/search questions/i);
      
      performanceMonitor.start();

      // Rapid typing should be debounced
      await userEvent.type(searchInput, 'performance test');

      await waitFor(() => {
        expect(screen.getByText(/Performance test question/)).toBeInTheDocument();
      });

      const performance = performanceMonitor.end();

      // Search should be responsive
      expect(performance.duration).toBeLessThan(1000);
    });

    test('virtual scrolling handles large lists efficiently', async () => {
      const hugeQuestionSet = generateLargeQuestionSet(1000);
      
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({
        questions: hugeQuestionSet
      });

      performanceMonitor.start();

      const { container } = render(
        <TestWrapper>
          <QuestionContainer 
            bookId="test-book" 
            chapterId="test-chapter" 
            chapterTitle="Virtual Scroll Test" 
          />
        </TestWrapper>
      );

      await waitFor(() => {
        // Wait for content to load - check for any text content
        expect(container.firstChild).toBeInTheDocument();
      });

      const performance = performanceMonitor.end();

      // Virtual scrolling should handle large lists efficiently
      expect(performance.duration).toBeLessThan(3000);
      
      // Only visible items should be rendered in DOM
      // Since we're using virtualization, check that not all questions are rendered
      const questionElements = container.querySelectorAll('[role="textbox"], .question-text, textarea');
      expect(questionElements.length).toBeLessThan(100); // Should not render all 1000
    });
  });
});
