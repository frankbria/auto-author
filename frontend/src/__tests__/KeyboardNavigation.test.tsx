import { render, screen, fireEvent, act } from '@testing-library/react';
import { ChapterTabs } from '@/components/chapters/ChapterTabs';
import ChapterQuestions from '@/components/chapters/questions/ChapterQuestions';
import { useChapterTabs } from '@/hooks/useChapterTabs';
import { generateChaptersFixture, setupTestEnvironment } from './fixtures/chapterTabsFixtures';
import { bookClient } from '@/lib/api/bookClient';

jest.mock('@/hooks/useChapterTabs');
const mockUseChapterTabs = useChapterTabs as jest.MockedFunction<typeof useChapterTabs>;

// Mock child components
jest.mock('@/components/chapters/TabBar', () => ({
  TabBar: () => <div data-testid="tab-bar">TabBar</div>
}));

jest.mock('@/components/chapters/TabContent', () => ({
  TabContent: () => <div data-testid="tab-content">TabContent</div>
}));

// Mock the API client for ChapterQuestions tests
jest.mock('@/lib/api/bookClient', () => ({
  bookClient: {
    getChapterQuestionProgress: jest.fn().mockResolvedValue({
      total: 10,
      completed: 3,
      in_progress: 2,
      progress: 0.3,
      status: 'in-progress'
    }),
  }
}));

// Mock QuestionContainer for ChapterQuestions tests
jest.mock('@/components/chapters/questions/QuestionContainer', () => {
  return function MockQuestionContainer() {
    return <div data-testid="question-container">Question Container Content</div>;
  };
});

describe('Keyboard Navigation', () => {
  beforeEach(() => {
    setupTestEnvironment();
    jest.clearAllMocks();
  });
  
  test('switches to corresponding tab when Ctrl+[number] is pressed', () => {
    // Setup
    const { chapters, tabOrder } = generateChaptersFixture(9);
    const setActiveChapterMock = jest.fn();
    const saveTabStateMock = jest.fn();
    
    mockUseChapterTabs.mockReturnValue({
      state: {
        chapters,
        active_chapter_id: 'ch-1',
        open_tab_ids: tabOrder,
        tab_order: tabOrder,
        is_loading: false,
        error: null
      },
      actions: {
        setActiveChapter: setActiveChapterMock,
        openTab: jest.fn(),
        reorderTabs: jest.fn(),
        closeTab: jest.fn(),
        updateChapterStatus: jest.fn(),
        saveTabState: saveTabStateMock,
        refreshChapters: jest.fn()
      },
      loading: false,
      error: null
    });
    
    // Render component
    render(<ChapterTabs bookId="test-book" />);
    
    // Simulate keyboard shortcuts
    fireEvent.keyDown(document, { key: '3', ctrlKey: true });
    
    // Verify correct tab was selected
    expect(setActiveChapterMock).toHaveBeenCalledWith('ch-3');
    expect(saveTabStateMock).toHaveBeenCalled();
  });
  
  test('handles out-of-range keyboard shortcuts gracefully', () => {
    // Setup with only 3 tabs
    const { chapters, tabOrder } = generateChaptersFixture(3);
    const setActiveChapterMock = jest.fn();
    
    mockUseChapterTabs.mockReturnValue({
      state: {
        chapters,
        active_chapter_id: 'ch-1',
        open_tab_ids: tabOrder,
        tab_order: tabOrder,
        is_loading: false,
        error: null
      },
      actions: {
        setActiveChapter: setActiveChapterMock,
        openTab: jest.fn(),
        reorderTabs: jest.fn(),
        closeTab: jest.fn(),
        updateChapterStatus: jest.fn(),
        saveTabState: jest.fn(),
        refreshChapters: jest.fn()
      },
      loading: false,
      error: null
    });
    
    // Render component
    render(<ChapterTabs bookId="test-book" />);
    
    // Simulate out-of-range keyboard shortcut
    fireEvent.keyDown(document, { key: '9', ctrlKey: true });
    
    // Verify setActiveChapter wasn't called
    expect(setActiveChapterMock).not.toHaveBeenCalled();
  });
  
  test('ignores non-ctrl key presses', () => {
    // Setup
    const { chapters, tabOrder } = generateChaptersFixture(5);
    const setActiveChapterMock = jest.fn();
    
    mockUseChapterTabs.mockReturnValue({
      state: {
        chapters,
        active_chapter_id: 'ch-1',
        open_tab_ids: tabOrder,
        tab_order: tabOrder,
        is_loading: false,
        error: null
      },
      actions: {
        setActiveChapter: setActiveChapterMock,
        openTab: jest.fn(),
        reorderTabs: jest.fn(),
        closeTab: jest.fn(),
        updateChapterStatus: jest.fn(),
        saveTabState: jest.fn(),
        refreshChapters: jest.fn()
      },
      loading: false,
      error: null
    });
    
    // Render component
    render(<ChapterTabs bookId="test-book" />);

    // Simulate non-ctrl key press
    fireEvent.keyDown(document, { key: '2', ctrlKey: false });

    // Verify setActiveChapter wasn't called
    expect(setActiveChapterMock).not.toHaveBeenCalled();
  });
});

describe('ChapterQuestions Keyboard Navigation', () => {
  const mockBookId = 'book123';
  const mockChapterId = 'chapter456';
  const mockChapterTitle = 'Test Chapter';

  beforeEach(() => {
    jest.clearAllMocks();
    sessionStorage.clear();
  });

  test('switches to questions tab with Ctrl+1', async () => {
    const onSwitchToEditor = jest.fn();
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

    // Press Ctrl+1
    await act(async () => {
      fireEvent.keyDown(document, { key: '1', ctrlKey: true });
    });

    // Questions tab should be active
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

    // Editor tab should be active
    const editorTab = screen.getByRole('tab', { name: /Chapter Editor/i });
    expect(editorTab).toHaveAttribute('aria-selected', 'true');
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

    // Press Ctrl+Tab
    await act(async () => {
      fireEvent.keyDown(document, { key: 'Tab', ctrlKey: true });
    });

    // Editor tab should be active
    const editorTab = screen.getByRole('tab', { name: /Chapter Editor/i });
    expect(editorTab).toHaveAttribute('aria-selected', 'true');
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

    // Press Ctrl+Shift+Tab (should wrap to editor)
    await act(async () => {
      fireEvent.keyDown(document, { key: 'Tab', ctrlKey: true, shiftKey: true });
    });

    // Editor tab should be active (wrapped from questions)
    const editorTab = screen.getByRole('tab', { name: /Chapter Editor/i });
    expect(editorTab).toHaveAttribute('aria-selected', 'true');
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
    expect(onSwitchToEditor).not.toHaveBeenCalled();
  });
});
