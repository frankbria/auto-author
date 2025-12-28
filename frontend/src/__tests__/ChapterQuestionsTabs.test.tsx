import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import ChapterQuestions from '@/components/chapters/questions/ChapterQuestions';
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

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({
    push: jest.fn(),
    replace: jest.fn(),
    back: jest.fn(),
  })),
}));

// Mock QuestionContainer to simplify tests
jest.mock('@/components/chapters/questions/QuestionContainer', () => {
  return function MockQuestionContainer() {
    return <div data-testid="question-container">Question Container Content</div>;
  };
});

describe('ChapterQuestions Tabs', () => {
  const mockBookId = 'book123';
  const mockChapterId = 'chapter456';
  const mockChapterTitle = 'Chapter 1: Getting Started';

  const mockProgress = {
    total: 10,
    completed: 3,
    in_progress: 2,
    progress: 0.3,
    status: 'in-progress'
  };

  beforeEach(() => {
    jest.clearAllMocks();
    sessionStorage.clear();
    (bookClient.getChapterQuestionProgress as jest.Mock).mockResolvedValue(mockProgress);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Tab Rendering', () => {
    test('renders tabs with correct initial state', async () => {
      const onSwitchToEditor = jest.fn();

      await act(async () => {
        render(
          <ChapterQuestions
            bookId={mockBookId}
            chapterId={mockChapterId}
            chapterTitle={mockChapterTitle}
            onSwitchToEditor={onSwitchToEditor}
          />
        );
      });

      // Check that tabs are rendered
      expect(screen.getByRole('tablist')).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Interview Questions/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Chapter Editor/i })).toBeInTheDocument();

      // Questions tab should be active by default
      const questionsTab = screen.getByRole('tab', { name: /Interview Questions/i });
      expect(questionsTab).toHaveAttribute('aria-selected', 'true');
    });

    test('renders only questions tab when onSwitchToEditor is not provided', async () => {
      await act(async () => {
        render(
          <ChapterQuestions
            bookId={mockBookId}
            chapterId={mockChapterId}
            chapterTitle={mockChapterTitle}
          />
        );
      });

      expect(screen.getByRole('tab', { name: /Interview Questions/i })).toBeInTheDocument();
      expect(screen.queryByRole('tab', { name: /Chapter Editor/i })).not.toBeInTheDocument();
    });
  });

  describe('Tab Switching', () => {
    test('switches tabs when clicking tab triggers', async () => {
      const onSwitchToEditor = jest.fn();
      const user = userEvent.setup();

      await act(async () => {
        render(
          <ChapterQuestions
            bookId={mockBookId}
            chapterId={mockChapterId}
            chapterTitle={mockChapterTitle}
            onSwitchToEditor={onSwitchToEditor}
          />
        );
      });

      const editorTab = screen.getByRole('tab', { name: /Chapter Editor/i });
      await user.click(editorTab);

      // Editor tab should now be active
      expect(editorTab).toHaveAttribute('aria-selected', 'true');

      // onSwitchToEditor should be called
      expect(onSwitchToEditor).toHaveBeenCalled();
    });

    test('calls onSwitchToEditor when switching to editor tab', async () => {
      const onSwitchToEditor = jest.fn();
      const user = userEvent.setup();

      await act(async () => {
        render(
          <ChapterQuestions
            bookId={mockBookId}
            chapterId={mockChapterId}
            chapterTitle={mockChapterTitle}
            onSwitchToEditor={onSwitchToEditor}
          />
        );
      });

      const editorTab = screen.getByRole('tab', { name: /Chapter Editor/i });
      await user.click(editorTab);

      expect(onSwitchToEditor).toHaveBeenCalledTimes(1);
    });
  });

  describe('Session Storage Persistence', () => {
    test('persists tab state to sessionStorage', async () => {
      const onSwitchToEditor = jest.fn();
      const user = userEvent.setup();

      await act(async () => {
        render(
          <ChapterQuestions
            bookId={mockBookId}
            chapterId={mockChapterId}
            chapterTitle={mockChapterTitle}
            onSwitchToEditor={onSwitchToEditor}
          />
        );
      });

      const editorTab = screen.getByRole('tab', { name: /Chapter Editor/i });
      await user.click(editorTab);

      const storageKey = `chapterQuestionsTab_${mockBookId}_${mockChapterId}`;
      expect(sessionStorage.getItem(storageKey)).toBe('editor');
    });

    test('restores tab state from sessionStorage on mount', async () => {
      const onSwitchToEditor = jest.fn();
      const storageKey = `chapterQuestionsTab_${mockBookId}_${mockChapterId}`;

      // Set editor tab as saved state
      sessionStorage.setItem(storageKey, 'editor');

      await act(async () => {
        render(
          <ChapterQuestions
            bookId={mockBookId}
            chapterId={mockChapterId}
            chapterTitle={mockChapterTitle}
            onSwitchToEditor={onSwitchToEditor}
          />
        );
      });

      // Editor tab should be active based on saved state
      const editorTab = screen.getByRole('tab', { name: /Chapter Editor/i });
      expect(editorTab).toHaveAttribute('aria-selected', 'true');
    });

    test('defaults to questions tab when no saved state', async () => {
      await act(async () => {
        render(
          <ChapterQuestions
            bookId={mockBookId}
            chapterId={mockChapterId}
            chapterTitle={mockChapterTitle}
            onSwitchToEditor={jest.fn()}
          />
        );
      });

      const questionsTab = screen.getByRole('tab', { name: /Interview Questions/i });
      expect(questionsTab).toHaveAttribute('aria-selected', 'true');
    });
  });

  describe('Keyboard Navigation', () => {
    test('switches to questions tab with Ctrl+1', async () => {
      const onSwitchToEditor = jest.fn();

      // Set editor tab as initial state
      const storageKey = `chapterQuestionsTab_${mockBookId}_${mockChapterId}`;
      sessionStorage.setItem(storageKey, 'editor');

      await act(async () => {
        render(
          <ChapterQuestions
            bookId={mockBookId}
            chapterId={mockChapterId}
            chapterTitle={mockChapterTitle}
            onSwitchToEditor={onSwitchToEditor}
          />
        );
      });

      // Verify editor tab is active initially
      const editorTab = screen.getByRole('tab', { name: /Chapter Editor/i });
      expect(editorTab).toHaveAttribute('aria-selected', 'true');

      // Press Ctrl+1
      await act(async () => {
        fireEvent.keyDown(document, { key: '1', ctrlKey: true });
      });

      // Questions tab should now be active
      const questionsTab = screen.getByRole('tab', { name: /Interview Questions/i });
      expect(questionsTab).toHaveAttribute('aria-selected', 'true');
    });

    test('switches to editor tab with Ctrl+2', async () => {
      const onSwitchToEditor = jest.fn();

      await act(async () => {
        render(
          <ChapterQuestions
            bookId={mockBookId}
            chapterId={mockChapterId}
            chapterTitle={mockChapterTitle}
            onSwitchToEditor={onSwitchToEditor}
          />
        );
      });

      // Press Ctrl+2
      await act(async () => {
        fireEvent.keyDown(document, { key: '2', ctrlKey: true });
      });

      // Editor tab should now be active
      const editorTab = screen.getByRole('tab', { name: /Chapter Editor/i });
      expect(editorTab).toHaveAttribute('aria-selected', 'true');

      // onSwitchToEditor should be called
      expect(onSwitchToEditor).toHaveBeenCalled();
    });

    test('cycles through tabs with Ctrl+Tab', async () => {
      const onSwitchToEditor = jest.fn();

      await act(async () => {
        render(
          <ChapterQuestions
            bookId={mockBookId}
            chapterId={mockChapterId}
            chapterTitle={mockChapterTitle}
            onSwitchToEditor={onSwitchToEditor}
          />
        );
      });

      // Questions tab should be active initially
      let questionsTab = screen.getByRole('tab', { name: /Interview Questions/i });
      expect(questionsTab).toHaveAttribute('aria-selected', 'true');

      // Press Ctrl+Tab to switch to next tab (editor)
      await act(async () => {
        fireEvent.keyDown(document, { key: 'Tab', ctrlKey: true });
      });

      const editorTab = screen.getByRole('tab', { name: /Chapter Editor/i });
      expect(editorTab).toHaveAttribute('aria-selected', 'true');

      // Press Ctrl+Tab again to cycle back to questions
      await act(async () => {
        fireEvent.keyDown(document, { key: 'Tab', ctrlKey: true });
      });

      questionsTab = screen.getByRole('tab', { name: /Interview Questions/i });
      expect(questionsTab).toHaveAttribute('aria-selected', 'true');
    });

    test('cycles backward with Ctrl+Shift+Tab', async () => {
      const onSwitchToEditor = jest.fn();

      await act(async () => {
        render(
          <ChapterQuestions
            bookId={mockBookId}
            chapterId={mockChapterId}
            chapterTitle={mockChapterTitle}
            onSwitchToEditor={onSwitchToEditor}
          />
        );
      });

      // Questions tab should be active initially
      const questionsTab = screen.getByRole('tab', { name: /Interview Questions/i });
      expect(questionsTab).toHaveAttribute('aria-selected', 'true');

      // Press Ctrl+Shift+Tab to switch to previous tab (editor, wrapping around)
      await act(async () => {
        fireEvent.keyDown(document, { key: 'Tab', ctrlKey: true, shiftKey: true });
      });

      const editorTab = screen.getByRole('tab', { name: /Chapter Editor/i });
      expect(editorTab).toHaveAttribute('aria-selected', 'true');
    });

    test('ignores Ctrl+2 when no editor callback provided', async () => {
      await act(async () => {
        render(
          <ChapterQuestions
            bookId={mockBookId}
            chapterId={mockChapterId}
            chapterTitle={mockChapterTitle}
          />
        );
      });

      // Press Ctrl+2 (should be ignored since no editor)
      await act(async () => {
        fireEvent.keyDown(document, { key: '2', ctrlKey: true });
      });

      // Questions tab should still be active
      const questionsTab = screen.getByRole('tab', { name: /Interview Questions/i });
      expect(questionsTab).toHaveAttribute('aria-selected', 'true');
    });

    test('ignores non-ctrl key presses', async () => {
      const onSwitchToEditor = jest.fn();

      await act(async () => {
        render(
          <ChapterQuestions
            bookId={mockBookId}
            chapterId={mockChapterId}
            chapterTitle={mockChapterTitle}
            onSwitchToEditor={onSwitchToEditor}
          />
        );
      });

      // Press just 2 (without Ctrl)
      await act(async () => {
        fireEvent.keyDown(document, { key: '2', ctrlKey: false });
      });

      // Questions tab should still be active
      const questionsTab = screen.getByRole('tab', { name: /Interview Questions/i });
      expect(questionsTab).toHaveAttribute('aria-selected', 'true');

      // onSwitchToEditor should not be called
      expect(onSwitchToEditor).not.toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    test('tabs have proper ARIA attributes', async () => {
      const onSwitchToEditor = jest.fn();

      await act(async () => {
        render(
          <ChapterQuestions
            bookId={mockBookId}
            chapterId={mockChapterId}
            chapterTitle={mockChapterTitle}
            onSwitchToEditor={onSwitchToEditor}
          />
        );
      });

      const tablist = screen.getByRole('tablist');
      expect(tablist).toBeInTheDocument();

      const questionsTab = screen.getByRole('tab', { name: /Interview Questions/i });
      const editorTab = screen.getByRole('tab', { name: /Chapter Editor/i });

      // Check aria-selected on active tab
      expect(questionsTab).toHaveAttribute('aria-selected', 'true');
      expect(editorTab).toHaveAttribute('aria-selected', 'false');

      // Check aria-controls on tabs (Radix UI manages this)
      expect(questionsTab).toHaveAttribute('aria-controls');
      expect(editorTab).toHaveAttribute('aria-controls');
    });

    test('tab panel has proper ARIA relationship with tab', async () => {
      await act(async () => {
        render(
          <ChapterQuestions
            bookId={mockBookId}
            chapterId={mockChapterId}
            chapterTitle={mockChapterTitle}
            onSwitchToEditor={jest.fn()}
          />
        );
      });

      const questionsTab = screen.getByRole('tab', { name: /Interview Questions/i });
      const tabpanel = screen.getByRole('tabpanel');

      // Tabpanel should be labeled by the tab
      expect(tabpanel).toHaveAttribute('aria-labelledby', questionsTab.id);
    });

    test('supports arrow key navigation within tabs', async () => {
      const onSwitchToEditor = jest.fn();
      const user = userEvent.setup();

      await act(async () => {
        render(
          <ChapterQuestions
            bookId={mockBookId}
            chapterId={mockChapterId}
            chapterTitle={mockChapterTitle}
            onSwitchToEditor={onSwitchToEditor}
          />
        );
      });

      const questionsTab = screen.getByRole('tab', { name: /Interview Questions/i });

      // Focus the tab
      questionsTab.focus();
      expect(questionsTab).toHaveFocus();

      // Arrow right should move to next tab (Radix UI handles this)
      await user.keyboard('{ArrowRight}');

      const editorTab = screen.getByRole('tab', { name: /Chapter Editor/i });
      expect(editorTab).toHaveFocus();
    });
  });

  describe('Content Display', () => {
    test('shows QuestionContainer in questions tab', async () => {
      await act(async () => {
        render(
          <ChapterQuestions
            bookId={mockBookId}
            chapterId={mockChapterId}
            chapterTitle={mockChapterTitle}
            onSwitchToEditor={jest.fn()}
          />
        );
      });

      expect(screen.getByTestId('question-container')).toBeInTheDocument();
    });

    test('displays chapter title', async () => {
      await act(async () => {
        render(
          <ChapterQuestions
            bookId={mockBookId}
            chapterId={mockChapterId}
            chapterTitle={mockChapterTitle}
            onSwitchToEditor={jest.fn()}
          />
        );
      });

      expect(screen.getByText(mockChapterTitle)).toBeInTheDocument();
    });

    test('displays progress when available', async () => {
      await act(async () => {
        render(
          <ChapterQuestions
            bookId={mockBookId}
            chapterId={mockChapterId}
            chapterTitle={mockChapterTitle}
            onSwitchToEditor={jest.fn()}
          />
        );
      });

      await waitFor(() => {
        expect(screen.getByText(/3 of 10 questions answered/i)).toBeInTheDocument();
      });
    });
  });
});
