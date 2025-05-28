import { render, screen } from '@testing-library/react';
import { ChapterTabs } from '@/components/chapters/ChapterTabs';

// Mock the useChapterTabs hook
jest.mock('@/hooks/useChapterTabs', () => ({
  useChapterTabs: jest.fn(() => ({
    state: {
      chapters: [
        {
          id: '1',
          title: 'Chapter 1',
          status: 'draft',
          last_modified: new Date().toISOString(),
          word_count: 1000,
          reading_time: 5,
          is_locked: false,
          metadata: {}
        }
      ],
      active_chapter_id: '1',
      tab_order: ['1'],
      unsaved_changes: {}
    },
    actions: {
      setActiveChapter: jest.fn(),
      reorderTabs: jest.fn(),
      closeTab: jest.fn(),
      updateChapterStatus: jest.fn(),
      saveTabState: jest.fn()
    },
    loading: false,
    error: null
  }))
}));

// Mock the child components
jest.mock('@/components/chapters/TabBar', () => ({
  TabBar: () => <div data-testid="tab-bar">TabBar</div>
}));

jest.mock('@/components/chapters/TabContent', () => ({
  TabContent: () => <div data-testid="tab-content">TabContent</div>
}));

jest.mock('@/components/chapters/TabContextMenu', () => ({
  __esModule: true,
  default: () => <div data-testid="tab-context-menu">TabContextMenu</div>
}));

describe('ChapterTabs', () => {
  it('should render without crashing', () => {
    render(<ChapterTabs bookId="test-book-id" />);
    
    expect(screen.getByTestId('tab-bar')).toBeInTheDocument();
    expect(screen.getByTestId('tab-content')).toBeInTheDocument();
    expect(screen.getByTestId('tab-context-menu')).toBeInTheDocument();
  });

  it('should accept className prop', () => {
    const { container } = render(
      <ChapterTabs bookId="test-book-id" className="custom-class" />
    );
    
    expect(container.firstChild).toHaveClass('custom-class');
  });
});
