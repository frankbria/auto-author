import { render, screen } from '@testing-library/react';
import { ChapterTabs } from '@/components/chapters/ChapterTabs';
import { useChapterTabs } from '@/hooks/useChapterTabs';
import { generateChaptersFixture, setupTestEnvironment } from './fixtures/chapterTabsFixtures';
import { useMediaQuery } from '@/hooks/use-media-query';
import { ChapterTabMetadata } from '@/types/chapter-tabs';

// Mock hooks
jest.mock('@/hooks/useChapterTabs');
jest.mock('@/hooks/use-media-query');

const mockUseChapterTabs = useChapterTabs as jest.MockedFunction<typeof useChapterTabs>;
const mockUseMediaQuery = useMediaQuery as jest.MockedFunction<typeof useMediaQuery>;

// Mock MobileChapterTabs component
jest.mock('@/components/chapters/MobileChapterTabs', () => ({
  MobileChapterTabs: ({ chapters }: { chapters: ChapterTabMetadata[] }) => (
    <div data-testid="mobile-tabs">
      Mobile View ({chapters.length} chapters)
    </div>
  )
}));

describe('Responsive Tab Layout', () => {
  beforeEach(() => {
    setupTestEnvironment();
    jest.clearAllMocks();
    
    // Default mock for tab state
    const { chapters, tabOrder } = generateChaptersFixture(5);
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
        setActiveChapter: jest.fn(),
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
  });
  
  test('renders desktop layout on large screens', () => {
    // Mock desktop viewport
    mockUseMediaQuery.mockReturnValue(false); // Not mobile
    
    render(<ChapterTabs bookId="test-book" />);
    
    // Verify desktop components are rendered
    expect(screen.queryByTestId('mobile-tabs')).not.toBeInTheDocument();
    expect(screen.getByTestId('tab-bar')).toBeInTheDocument();
  });
  
  test('renders mobile layout on small screens', () => {
    // Mock mobile viewport
    mockUseMediaQuery.mockReturnValue(true); // Is mobile
    
    render(<ChapterTabs bookId="test-book" />);
    
    // Verify mobile components are rendered
    expect(screen.getByTestId('mobile-tabs')).toBeInTheDocument();
    expect(screen.queryByTestId('tab-bar')).not.toBeInTheDocument();
  });
  
  test('passes correct props to mobile and desktop components', () => {
    // Test desktop first
    mockUseMediaQuery.mockReturnValue(false);
    
    const { unmount } = render(<ChapterTabs bookId="test-book" />);
    
    // Verify desktop component receives correct props
    expect(screen.getByTestId('tab-bar')).toBeInTheDocument();
    
    // Unmount and test mobile
    unmount();
    mockUseMediaQuery.mockReturnValue(true);
    
    render(<ChapterTabs bookId="test-book" />);
    
    // Verify mobile component receives correct props
    expect(screen.getByTestId('mobile-tabs')).toHaveTextContent('Mobile View (5 chapters)');
  });
});
