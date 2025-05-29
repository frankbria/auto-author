import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { ChapterTabs } from '@/components/chapters/ChapterTabs';
import { useChapterTabs } from '@/hooks/useChapterTabs';
import { ChapterStatus } from '@/types/chapter-tabs';

// Mock the hooks
jest.mock('@/hooks/useChapterTabs');
const mockUseChapterTabs = useChapterTabs as jest.MockedFunction<typeof useChapterTabs>;

// Mock the API clients used in the hooks
jest.mock('@/lib/api/bookClient', () => ({
  __esModule: true,
  default: {
    getToc: jest.fn(),
    setAuthToken: jest.fn(),
    getChaptersMetadata: jest.fn(),
    getTabState: jest.fn(),
    saveTabState: jest.fn(),
    updateChapterStatus: jest.fn(),
  },
}));

describe('ChapterTabs TOC Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('correctly renders chapters from TOC structure', async () => {
    // Setup mock hook return value with TOC-sourced data
    mockUseChapterTabs.mockReturnValue({
      state: {
        chapters: [
          {
            id: 'ch1',
            title: 'Introduction',
            status: ChapterStatus.DRAFT,
            word_count: 0,
            last_modified: new Date().toISOString(),
            estimated_reading_time: 0,
            level: 1,
            order: 1,
            has_content: false,
          },
          {
            id: 'ch2',
            title: 'Main Content',
            status: ChapterStatus.IN_PROGRESS,
            word_count: 500,
            last_modified: new Date().toISOString(),
            estimated_reading_time: 3,
            level: 1,
            order: 2,
            has_content: true,
          },
          {
            id: 'ch2-1',
            title: 'Subchapter',
            status: ChapterStatus.DRAFT,
            word_count: 0,
            last_modified: new Date().toISOString(),
            estimated_reading_time: 0,
            level: 2,
            order: 1,
            has_content: false,
          },
        ],
        active_chapter_id: 'ch1',
        open_tab_ids: ['ch1', 'ch2'],
        tab_order: ['ch1', 'ch2'],
        is_loading: false,        error: null,
      },
      actions: {
        setActiveChapter: jest.fn(),
        openTab: jest.fn(),
        reorderTabs: jest.fn(),
        closeTab: jest.fn(),
        updateChapterStatus: jest.fn(),
        saveTabState: jest.fn(),
        refreshChapters: jest.fn(),
      },
      loading: false,
      error: null,
    });

    render(<ChapterTabs bookId="test-book-id" />);

    // Wait for and verify tabs are rendered with correct titles
    await waitFor(() => {
      expect(screen.getByText('Introduction')).toBeInTheDocument();
      expect(screen.getByText('Main Content')).toBeInTheDocument();
    });
  });

  it('shows loading state while fetching TOC data', async () => {
    // Mock the loading state
    mockUseChapterTabs.mockReturnValue({
      state: {
        chapters: [],
        active_chapter_id: null,
        open_tab_ids: [],
        tab_order: [],
        is_loading: true,
        error: null,
      },      actions: {
        setActiveChapter: jest.fn(),
        openTab: jest.fn(),
        reorderTabs: jest.fn(),
        closeTab: jest.fn(),
        updateChapterStatus: jest.fn(),
        saveTabState: jest.fn(),
        refreshChapters: jest.fn(),
      },
      loading: true,
      error: null,
    });

    render(<ChapterTabs bookId="test-book-id" />);
    
    // Verify loading state is shown
    expect(screen.getByText('Loading chapters...')).toBeInTheDocument();
  });

  it('shows error state when TOC or chapter data fetch fails', async () => {
    // Mock the error state
    mockUseChapterTabs.mockReturnValue({
      state: {
        chapters: [],
        active_chapter_id: null,
        open_tab_ids: [],
        tab_order: [],
        is_loading: false,
        error: 'Failed to load TOC data',
      },      actions: {
        setActiveChapter: jest.fn(),
        openTab: jest.fn(),
        reorderTabs: jest.fn(),
        closeTab: jest.fn(),
        updateChapterStatus: jest.fn(),
        saveTabState: jest.fn(),
        refreshChapters: jest.fn(),
      },
      loading: false,
      error: 'Failed to load TOC data',
    });

    render(<ChapterTabs bookId="test-book-id" />);
    
    // Verify error state is shown
    expect(screen.getByText('Error loading chapters')).toBeInTheDocument();
    expect(screen.getByText('Failed to load TOC data')).toBeInTheDocument();
  });
});
