import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import QuestionContainer from '@/components/chapters/questions/QuestionContainer';
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
  }
}));

// Mock the Toast component
jest.mock('@/components/ui/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn()
  })
}));

describe('Question Components', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('QuestionContainer', () => {
    const mockQuestions = [
      {
        id: 'question1',
        chapter_id: 'chapter1',
        question_text: 'What is the main character\'s motivation?',
        question_type: QuestionType.CHARACTER,
        difficulty: QuestionDifficulty.MEDIUM,
        category: 'development',
        order: 1,
        generated_at: '2023-01-01T00:00:00Z',
        metadata: {
          suggested_response_length: '200-300 words',
          help_text: 'Think about internal and external motivations.',
          examples: ['Example answer 1', 'Example answer 2']
        },
        has_response: false
      },
      {
        id: 'question2',
        chapter_id: 'chapter1',
        question_text: 'Describe the setting of this chapter.',
        question_type: QuestionType.SETTING,
        difficulty: QuestionDifficulty.EASY,
        category: 'development',
        order: 2,
        generated_at: '2023-01-01T00:00:00Z',
        metadata: {
          suggested_response_length: '100-200 words',
        },
        has_response: true,
        response_status: ResponseStatus.COMPLETED
      }
    ];

    const mockProgress = {
      total: 10,
      completed: 2,
      in_progress: 1,
      progress: 0.3,
      status: 'in-progress'
    };

    test('renders empty state when no questions', async () => {
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({ questions: [] });
      
      render(
        <QuestionContainer 
          bookId="book1" 
          chapterId="chapter1" 
          chapterTitle="Chapter 1: Introduction" 
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Interview Questions')).toBeInTheDocument();
        expect(screen.getByText(/Generate interview-style questions/)).toBeInTheDocument();
      });
    });

    test('renders questions when available', async () => {
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({ questions: mockQuestions });
      (bookClient.getChapterQuestionProgress as jest.Mock).mockResolvedValue(mockProgress);
      (bookClient.getQuestionResponse as jest.Mock).mockResolvedValue({ 
        has_response: false, 
        response: null 
      });
      
      render(
        <QuestionContainer 
          bookId="book1" 
          chapterId="chapter1" 
          chapterTitle="Chapter 1: Introduction" 
        />
      );

      await waitFor(() => {
        expect(screen.getByText('What is the main character\'s motivation?')).toBeInTheDocument();
      });
    });

    test('handles question generation', async () => {
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({ questions: [] });
      (bookClient.generateChapterQuestions as jest.Mock).mockResolvedValue({ 
        questions: mockQuestions,
        total: 2,
        generation_id: 'gen1'
      });
      (bookClient.getChapterQuestionProgress as jest.Mock).mockResolvedValue(mockProgress);
      
      render(
        <QuestionContainer 
          bookId="book1" 
          chapterId="chapter1" 
          chapterTitle="Chapter 1: Introduction" 
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/Generate interview-style questions/)).toBeInTheDocument();
      });

      // Find and click the generate button
      const generateButton = screen.getByText(/Generate/);
      fireEvent.click(generateButton);

      await waitFor(() => {
        expect(bookClient.generateChapterQuestions).toHaveBeenCalledWith(
          'book1', 
          'chapter1', 
          expect.anything()
        );
      });
    });

    test('handles saving responses', async () => {
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({ questions: mockQuestions });
      (bookClient.getChapterQuestionProgress as jest.Mock).mockResolvedValue(mockProgress);
      (bookClient.getQuestionResponse as jest.Mock).mockResolvedValue({ 
        has_response: false, 
        response: null 
      });
      (bookClient.saveQuestionResponse as jest.Mock).mockResolvedValue({
        response: {
          id: 'resp1',
          question_id: 'question1',
          response_text: 'Test response',
          word_count: 2,
          status: ResponseStatus.COMPLETED,
          created_at: '2023-01-01T00:00:00Z',
          updated_at: '2023-01-01T00:00:00Z',
          last_edited_at: '2023-01-01T00:00:00Z',
          metadata: {
            edit_history: []
          }
        },
        success: true,
        message: 'Response saved'
      });
      
      render(
        <QuestionContainer 
          bookId="book1" 
          chapterId="chapter1" 
          chapterTitle="Chapter 1: Introduction" 
        />
      );

      await waitFor(() => {
        expect(screen.getByText('What is the main character\'s motivation?')).toBeInTheDocument();
      });

      // Find and type in the text area
      const textarea = screen.getByPlaceholderText('Write your answer here...');
      fireEvent.change(textarea, { target: { value: 'Test response' } });

      // Find and click the save button
      const saveButton = screen.getByText('Save Answer');
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(bookClient.saveQuestionResponse).toHaveBeenCalledWith(
          'book1',
          'chapter1',
          'question1',
          expect.objectContaining({
            response_text: 'Test response',
            status: expect.anything()
          })
        );
      });
    });

    test('handles navigation between questions', async () => {
      (bookClient.getChapterQuestions as jest.Mock).mockResolvedValue({ questions: mockQuestions });
      (bookClient.getChapterQuestionProgress as jest.Mock).mockResolvedValue(mockProgress);
      (bookClient.getQuestionResponse as jest.Mock).mockResolvedValue({ 
        has_response: false, 
        response: null 
      });
      
      render(
        <QuestionContainer 
          bookId="book1" 
          chapterId="chapter1" 
          chapterTitle="Chapter 1: Introduction" 
        />
      );

      await waitFor(() => {
        expect(screen.getByText('What is the main character\'s motivation?')).toBeInTheDocument();
      });

      // Click next button to go to next question
      const nextButton = screen.getByText('Next');
      fireEvent.click(nextButton);

      await waitFor(() => {
        expect(screen.getByText('Describe the setting of this chapter.')).toBeInTheDocument();
      });

      // Click previous button to go back
      const prevButton = screen.getByText('Previous');
      fireEvent.click(prevButton);

      await waitFor(() => {
        expect(screen.getByText('What is the main character\'s motivation?')).toBeInTheDocument();
      });
    });
  });
});
