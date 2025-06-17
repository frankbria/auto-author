import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import QuestionDisplay from '../components/chapters/questions/QuestionDisplay';
import { Question, QuestionType, QuestionDifficulty, ResponseStatus } from '../types/chapter-questions';
import bookClient from '../lib/api/bookClient';

// Mock the bookClient
jest.mock('../lib/api/bookClient', () => ({
  __esModule: true,
  default: {
    getQuestionResponse: jest.fn(),
    saveQuestionResponse: jest.fn(),
    rateQuestion: jest.fn(),
  },
  bookClient: {
    getQuestionResponse: jest.fn(),
    saveQuestionResponse: jest.fn(),
    rateQuestion: jest.fn(),
  }
}));

describe('VoiceTextInput Integration in QuestionDisplay', () => {
  const mockQuestion: Question = {
    id: 'q1',
    chapter_id: 'ch1',
    question_text: 'What are the main themes of your book?',
    question_type: QuestionType.THEME,
    difficulty: QuestionDifficulty.MEDIUM,
    order: 1,
    generated_at: '2025-01-01T00:00:00Z',
    metadata: {
      suggested_response_length: '150-200 words',
      help_text: 'Think about the central ideas you want to explore.',
      examples: ['Coming of age', 'Identity and belonging']
    }
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (bookClient.getQuestionResponse as jest.Mock).mockResolvedValue({
      has_response: false,
      response: null
    });
    (bookClient.saveQuestionResponse as jest.Mock).mockResolvedValue({
      success: true
    });
  });

  test('renders VoiceTextInput component with correct placeholder', async () => {
    render(
      <QuestionDisplay
        bookId="book1"
        chapterId="ch1"
        question={mockQuestion}
        onResponseSaved={jest.fn()}
        onRegenerateQuestion={jest.fn()}
      />
    );

    // Wait for component to load
    await waitFor(() => {
      expect(screen.getByText(mockQuestion.question_text)).toBeInTheDocument();
    });

    // Check for VoiceTextInput placeholder
    const input = screen.getByPlaceholderText('Type your response here or use voice input...');
    expect(input).toBeInTheDocument();
  });

  test('shows voice input toggle button', async () => {
    render(
      <QuestionDisplay
        bookId="book1"
        chapterId="ch1"
        question={mockQuestion}
        onResponseSaved={jest.fn()}
        onRegenerateQuestion={jest.fn()}
      />
    );

    // Wait for component to load
    await waitFor(() => {
      expect(screen.getByText(mockQuestion.question_text)).toBeInTheDocument();
    });

    // Check for voice toggle button
    const voiceToggle = screen.getByText('Switch to Voice');
    expect(voiceToggle).toBeInTheDocument();
  });

  test('can type in the VoiceTextInput component', async () => {
    const user = userEvent.setup();
    
    render(
      <QuestionDisplay
        bookId="book1"
        chapterId="ch1"
        question={mockQuestion}
        onResponseSaved={jest.fn()}
        onRegenerateQuestion={jest.fn()}
      />
    );

    // Wait for component to load
    await waitFor(() => {
      expect(screen.getByText(mockQuestion.question_text)).toBeInTheDocument();
    });

    // Type in the input
    const input = screen.getByPlaceholderText('Type your response here or use voice input...');
    await user.type(input, 'This is my response text');

    // Verify the text was entered
    expect(input).toHaveValue('This is my response text');
  });

  test('triggers auto-save when typing', async () => {
    const user = userEvent.setup();
    const mockOnResponseSaved = jest.fn();
    
    render(
      <QuestionDisplay
        bookId="book1"
        chapterId="ch1"
        question={mockQuestion}
        onResponseSaved={mockOnResponseSaved}
        onRegenerateQuestion={jest.fn()}
      />
    );

    // Wait for component to load
    await waitFor(() => {
      expect(screen.getByText(mockQuestion.question_text)).toBeInTheDocument();
    });

    // Type in the input
    const input = screen.getByPlaceholderText('Type your response here or use voice input...');
    await user.type(input, 'This is my response text');

    // Wait for auto-save (3 seconds delay)
    await waitFor(() => {
      expect(bookClient.saveQuestionResponse).toHaveBeenCalledWith(
        'book1',
        'ch1',
        'q1',
        expect.objectContaining({
          response_text: 'This is my response text',
          status: ResponseStatus.DRAFT
        })
      );
    }, { timeout: 6000 });
  });

  test('can toggle between text and voice modes', async () => {
    render(
      <QuestionDisplay
        bookId="book1"
        chapterId="ch1"
        question={mockQuestion}
        onResponseSaved={jest.fn()}
        onRegenerateQuestion={jest.fn()}
      />
    );

    // Wait for component to load
    await waitFor(() => {
      expect(screen.getByText(mockQuestion.question_text)).toBeInTheDocument();
    });

    // Initially in text mode
    expect(screen.getByText('Switch to Voice')).toBeInTheDocument();
    
    // Click to switch to voice mode
    const toggleButton = screen.getByText('Switch to Voice');
    fireEvent.click(toggleButton);

    // Should now show switch to text option
    expect(screen.getByText('Switch to Text')).toBeInTheDocument();
  });
});