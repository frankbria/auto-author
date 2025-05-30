import { render, fireEvent } from '@testing-library/react';
import { ChapterTabs } from '@/components/chapters/ChapterTabs';
import { useChapterTabs } from '@/hooks/useChapterTabs';
import { generateChaptersFixture, setupTestEnvironment } from './fixtures/chapterTabsFixtures';

jest.mock('@/hooks/useChapterTabs');
const mockUseChapterTabs = useChapterTabs as jest.MockedFunction<typeof useChapterTabs>;

// Mock child components
jest.mock('@/components/chapters/TabBar', () => ({
  TabBar: () => <div data-testid="tab-bar">TabBar</div>
}));

jest.mock('@/components/chapters/TabContent', () => ({
  TabContent: () => <div data-testid="tab-content">TabContent</div>
}));

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
