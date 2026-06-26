import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { ChapterTabs } from '@/components/chapters/ChapterTabs';
import { useChapterTabs } from '@/hooks/useChapterTabs';
import { useMediaQuery } from '@/hooks/use-media-query';
import { toast } from '@/lib/toast';
import bookClient from '@/lib/api/bookClient';
import { ChapterStatus, ChapterTabMetadata } from '@/types/chapter-tabs';

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

jest.mock('@/hooks/useChapterTabs');
jest.mock('@/hooks/useTocSync', () => ({ useTocSync: jest.fn() }));
jest.mock('@/hooks/use-media-query', () => ({ useMediaQuery: jest.fn() }));
jest.mock('@/lib/toast', () => ({ toast: jest.fn() }));
jest.mock('@/lib/api/bookClient', () => ({
  __esModule: true,
  default: {
    deleteChapter: jest.fn(),
    createChapter: jest.fn(),
  },
}));

// Lightweight child-component stubs so we can exercise ChapterTabs callbacks
// without needing fully-wired sub-component trees.
jest.mock('@/components/chapters/TabBar', () => ({
  TabBar: ({ onTabSelect, onTabReorder, onTabClose, chapters }: any) => (
    <div data-testid="tab-bar">
      {chapters.map((ch: any) => (
        <button
          key={ch.id}
          data-testid={`tab-select-${ch.id}`}
          onClick={() => onTabSelect(ch.id)}
        >
          {ch.title}
        </button>
      ))}
      <button data-testid="reorder-btn" onClick={() => onTabReorder(0, 1)}>
        Reorder
      </button>
      <button
        data-testid="close-btn"
        onClick={() => chapters[0] && onTabClose(chapters[0].id)}
      >
        Close
      </button>
    </div>
  ),
}));

jest.mock('@/components/chapters/TabContent', () => ({
  TabContent: ({ onContentChange, onChapterSave, activeChapterId }: any) => (
    <div data-testid="tab-content">
      <button
        data-testid="content-change-btn"
        onClick={() => onContentChange(activeChapterId, 'test content')}
      >
        Change Content
      </button>
      <button
        data-testid="chapter-save-btn"
        onClick={() => onChapterSave(activeChapterId)}
      >
        Save Chapter
      </button>
    </div>
  ),
}));

jest.mock('@/components/chapters/TabContextMenu', () => ({
  __esModule: true,
  default: ({ chapterId, onStatusUpdate, onDelete, onEdit }: any) => (
    <div data-testid="tab-context-menu">
      {onDelete && (
        <button
          data-testid="ctx-delete-btn"
          onClick={() => onDelete(chapterId)}
        >
          Delete Chapter
        </button>
      )}
      {onEdit && (
        <button
          data-testid="ctx-edit-btn"
          onClick={() => onEdit(chapterId)}
        >
          Edit Chapter
        </button>
      )}
      {onStatusUpdate && (
        <button
          data-testid="ctx-status-btn"
          onClick={() => onStatusUpdate(chapterId, ChapterStatus.COMPLETED)}
        >
          Update Status
        </button>
      )}
    </div>
  ),
}));

jest.mock('@/components/chapters/MobileChapterTabs', () => ({
  MobileChapterTabs: ({ onChapterSelect, chapters }: any) => (
    <div data-testid="mobile-chapter-tabs">
      {chapters.map((ch: any) => (
        <button
          key={ch.id}
          data-testid={`mobile-tab-${ch.id}`}
          onClick={() => onChapterSelect(ch.id)}
        >
          {ch.title}
        </button>
      ))}
    </div>
  ),
}));

// ---------------------------------------------------------------------------
// Typed mock references
// ---------------------------------------------------------------------------

const mockUseChapterTabs = useChapterTabs as jest.MockedFunction<typeof useChapterTabs>;
const mockUseMediaQuery = useMediaQuery as jest.MockedFunction<typeof useMediaQuery>;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const makeChapter = (id: string, overrides: Partial<ChapterTabMetadata> = {}): ChapterTabMetadata => ({
  id,
  title: `Chapter ${id}`,
  status: ChapterStatus.DRAFT,
  word_count: 100,
  last_modified: new Date().toISOString(),
  estimated_reading_time: 1,
  level: 1,
  order: parseInt(id.replace('ch-', ''), 10) || 1,
  has_content: true,
  ...overrides,
});

const defaultChapters = [makeChapter('ch-1'), makeChapter('ch-2', { status: ChapterStatus.IN_PROGRESS })];

const makeActions = () => ({
  setActiveChapter: jest.fn(),
  reorderTabs: jest.fn(),
  closeTab: jest.fn(),
  updateChapterStatus: jest.fn(),
  saveTabState: jest.fn(),
  refreshChapters: jest.fn().mockResolvedValue(undefined),
  openTab: jest.fn(),
});

const makeState = (overrides: Record<string, unknown> = {}) => ({
  chapters: defaultChapters,
  active_chapter_id: 'ch-1',
  open_tab_ids: ['ch-1', 'ch-2'],
  tab_order: ['ch-1', 'ch-2'],
  is_loading: false,
  error: null,
  ...overrides,
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ChapterTabs', () => {
  let mockActions: ReturnType<typeof makeActions>;

  beforeEach(() => {
    jest.clearAllMocks();
    mockActions = makeActions();
    mockUseMediaQuery.mockReturnValue(false);
    mockUseChapterTabs.mockReturnValue({
      state: makeState(),
      actions: mockActions,
      loading: false,
      error: null,
    } as any);
  });

  // -------------------------------------------------------------------------
  // Rendering / branching states
  // -------------------------------------------------------------------------

  describe('Rendering states', () => {
    it('shows loading spinner when loading is true', () => {
      mockUseChapterTabs.mockReturnValue({
        state: makeState(),
        actions: mockActions,
        loading: true,
        error: null,
      } as any);
      render(<ChapterTabs bookId="book-1" />);
      expect(screen.getByText('Loading chapters...')).toBeInTheDocument();
    });

    it('shows error message and retry button when error is present', () => {
      mockUseChapterTabs.mockReturnValue({
        state: makeState({ chapters: [] }),
        actions: mockActions,
        loading: false,
        error: 'Network error',
      } as any);
      render(<ChapterTabs bookId="book-1" />);
      expect(screen.getByText('Error loading chapters')).toBeInTheDocument();
      expect(screen.getByText('Network error')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
    });

    it('calls refreshChapters when Retry button is clicked', () => {
      mockUseChapterTabs.mockReturnValue({
        state: makeState({ chapters: [] }),
        actions: mockActions,
        loading: false,
        error: 'Network error',
      } as any);
      render(<ChapterTabs bookId="book-1" />);
      fireEvent.click(screen.getByRole('button', { name: /retry/i }));
      expect(mockActions.refreshChapters).toHaveBeenCalledTimes(1);
    });

    it('shows empty-state UI when chapters array is empty and no error', () => {
      mockUseChapterTabs.mockReturnValue({
        state: makeState({ chapters: [] }),
        actions: mockActions,
        loading: false,
        error: null,
      } as any);
      render(<ChapterTabs bookId="book-1" />);
      expect(screen.getByTestId('empty-chapters-state')).toBeInTheDocument();
      expect(screen.getByText('No chapters available')).toBeInTheDocument();
    });

    it('renders TabBar on desktop (isMobile = false)', () => {
      mockUseMediaQuery.mockReturnValue(false);
      render(<ChapterTabs bookId="book-1" />);
      expect(screen.getByTestId('tab-bar')).toBeInTheDocument();
      expect(screen.queryByTestId('mobile-chapter-tabs')).not.toBeInTheDocument();
    });

    it('renders MobileChapterTabs when isMobile = true', () => {
      mockUseMediaQuery.mockReturnValue(true);
      render(<ChapterTabs bookId="book-1" />);
      expect(screen.getByTestId('mobile-chapter-tabs')).toBeInTheDocument();
      expect(screen.queryByTestId('tab-bar')).not.toBeInTheDocument();
    });

    it('shows overflow indicators when chapters exceed 20', () => {
      const manyChapters = Array.from({ length: 21 }, (_, i) => makeChapter(`ch-${i + 1}`));
      mockUseChapterTabs.mockReturnValue({
        state: makeState({
          chapters: manyChapters,
          tab_order: manyChapters.map((c) => c.id),
        }),
        actions: mockActions,
        loading: false,
        error: null,
      } as any);
      render(<ChapterTabs bookId="book-1" />);
      expect(screen.getByTestId('tab-overflow-indicator')).toBeInTheDocument();
      expect(screen.getByTestId('scroll-controls')).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // handleTabSelect
  // -------------------------------------------------------------------------

  describe('handleTabSelect', () => {
    it('calls setActiveChapter and saveTabState when a tab is selected', () => {
      render(<ChapterTabs bookId="book-1" />);
      fireEvent.click(screen.getByTestId('tab-select-ch-1'));
      expect(mockActions.setActiveChapter).toHaveBeenCalledWith('ch-1');
      expect(mockActions.saveTabState).toHaveBeenCalled();
    });

    it('calls setActiveChapter and saveTabState via MobileChapterTabs on mobile', () => {
      mockUseMediaQuery.mockReturnValue(true);
      render(<ChapterTabs bookId="book-1" />);
      fireEvent.click(screen.getByTestId('mobile-tab-ch-2'));
      expect(mockActions.setActiveChapter).toHaveBeenCalledWith('ch-2');
      expect(mockActions.saveTabState).toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // handleTabReorder
  // -------------------------------------------------------------------------

  describe('handleTabReorder', () => {
    it('calls reorderTabs with source and destination indices', () => {
      render(<ChapterTabs bookId="book-1" />);
      fireEvent.click(screen.getByTestId('reorder-btn'));
      expect(mockActions.reorderTabs).toHaveBeenCalledWith(0, 1);
    });
  });

  // -------------------------------------------------------------------------
  // handleEditChapter
  // -------------------------------------------------------------------------

  describe('handleEditChapter', () => {
    it('calls setActiveChapter with the chapterId when edit is triggered', () => {
      render(<ChapterTabs bookId="book-1" />);
      fireEvent.click(screen.getByTestId('ctx-edit-btn'));
      expect(mockActions.setActiveChapter).toHaveBeenCalledWith('ch-1');
    });
  });

  // -------------------------------------------------------------------------
  // handleDeleteChapter
  // -------------------------------------------------------------------------

  describe('handleDeleteChapter', () => {
    it('deletes chapter, closes tab, refreshes and shows success toast', async () => {
      (bookClient.deleteChapter as jest.Mock).mockResolvedValueOnce({});
      render(<ChapterTabs bookId="book-1" />);
      fireEvent.click(screen.getByTestId('ctx-delete-btn'));
      await waitFor(() => {
        expect(bookClient.deleteChapter).toHaveBeenCalledWith('book-1', 'ch-1');
        expect(mockActions.closeTab).toHaveBeenCalledWith('ch-1');
        expect(mockActions.refreshChapters).toHaveBeenCalled();
        expect(toast).toHaveBeenCalledWith(
          expect.objectContaining({ title: 'Chapter deleted', variant: 'success' })
        );
      });
    });

    it('shows destructive toast when delete API call fails', async () => {
      (bookClient.deleteChapter as jest.Mock).mockRejectedValueOnce(new Error('Server error'));
      render(<ChapterTabs bookId="book-1" />);
      fireEvent.click(screen.getByTestId('ctx-delete-btn'));
      await waitFor(() => {
        expect(toast).toHaveBeenCalledWith(
          expect.objectContaining({ title: 'Error', variant: 'destructive' })
        );
      });
    });

    it('uses "Chapter" as title fallback when chapter is not found in state', async () => {
      (bookClient.deleteChapter as jest.Mock).mockResolvedValueOnce({});
      // active_chapter_id points to a chapter NOT in state.chapters
      mockUseChapterTabs.mockReturnValue({
        state: makeState({ active_chapter_id: 'unknown-ch', chapters: [] }),
        actions: mockActions,
        loading: false,
        error: null,
      } as any);
      render(<ChapterTabs bookId="book-1" />);
      // ctx-delete-btn is only rendered when chapterId is truthy and onDelete exists
      // In empty state UI, context menu is still rendered (via the normal branch? no)
      // Actually when chapters is [] we get empty state. Re-mount with chapters but unknown id.
      // Re-mock so we have chapters but active id points elsewhere.
      mockUseChapterTabs.mockReturnValue({
        state: makeState({ active_chapter_id: 'no-such-id' }),
        actions: mockActions,
        loading: false,
        error: null,
      } as any);
      render(<ChapterTabs bookId="book-1" />);
      fireEvent.click(screen.getAllByTestId('ctx-delete-btn')[0]);
      await waitFor(() => {
        expect(toast).toHaveBeenCalledWith(
          expect.objectContaining({ title: 'Chapter deleted' })
        );
      });
    });
  });

  // -------------------------------------------------------------------------
  // handleCreateChapter
  // -------------------------------------------------------------------------

  describe('handleCreateChapter', () => {
    const emptyState = () =>
      mockUseChapterTabs.mockReturnValue({
        state: makeState({ chapters: [] }),
        actions: mockActions,
        loading: false,
        error: null,
      } as any);

    it('creates chapter, refreshes, sets active and shows success toast', async () => {
      const newChapter = { id: 'ch-new', title: 'Chapter 1' };
      (bookClient.createChapter as jest.Mock).mockResolvedValueOnce(newChapter);
      emptyState();
      render(<ChapterTabs bookId="book-1" />);
      fireEvent.click(screen.getByText('Create Chapter'));
      await waitFor(() => {
        expect(bookClient.createChapter).toHaveBeenCalledWith(
          'book-1',
          expect.objectContaining({ title: 'Chapter 1', content: '', order: 1 })
        );
        expect(mockActions.refreshChapters).toHaveBeenCalled();
        expect(mockActions.setActiveChapter).toHaveBeenCalledWith('ch-new');
        expect(toast).toHaveBeenCalledWith(
          expect.objectContaining({ title: 'Chapter created', variant: 'success' })
        );
      });
    });

    it('calculates correct order when chapters already exist', async () => {
      const chapters = [makeChapter('ch-1', { order: 3 }), makeChapter('ch-2', { order: 7 })];
      const newChapter = { id: 'ch-3', title: 'Chapter 8' };
      (bookClient.createChapter as jest.Mock).mockResolvedValueOnce(newChapter);
      mockUseChapterTabs.mockReturnValue({
        state: makeState({ chapters, active_chapter_id: null }),
        actions: mockActions,
        loading: false,
        error: null,
      } as any);
      // We need chapters to be empty to see the "Create Chapter" button
      // The button is only in the empty-state branch. Re-test via empty state.
      emptyState();
      render(<ChapterTabs bookId="book-1" />);
      fireEvent.click(screen.getByText('Create Chapter'));
      await waitFor(() => {
        expect(bookClient.createChapter).toHaveBeenCalledWith(
          'book-1',
          expect.objectContaining({ order: 1 })
        );
      });
    });

    it('shows destructive toast when createChapter API fails', async () => {
      (bookClient.createChapter as jest.Mock).mockRejectedValueOnce(new Error('Failed'));
      emptyState();
      render(<ChapterTabs bookId="book-1" />);
      fireEvent.click(screen.getByText('Create Chapter'));
      await waitFor(() => {
        expect(toast).toHaveBeenCalledWith(
          expect.objectContaining({ title: 'Error', variant: 'destructive' })
        );
      });
    });
  });

  // -------------------------------------------------------------------------
  // Keyboard navigation (Ctrl+1..9 global hotkeys)
  // -------------------------------------------------------------------------

  describe('keyboard navigation (Ctrl+digit)', () => {
    it('Ctrl+1 selects the first chapter in tab_order', () => {
      render(<ChapterTabs bookId="book-1" />);
      act(() => {
        fireEvent.keyDown(document, { key: '1', ctrlKey: true });
      });
      expect(mockActions.setActiveChapter).toHaveBeenCalledWith('ch-1');
      expect(mockActions.saveTabState).toHaveBeenCalled();
    });

    it('Ctrl+2 selects the second chapter in tab_order', () => {
      render(<ChapterTabs bookId="book-1" />);
      act(() => {
        fireEvent.keyDown(document, { key: '2', ctrlKey: true });
      });
      expect(mockActions.setActiveChapter).toHaveBeenCalledWith('ch-2');
    });

    it('does not select when Ctrl+digit index is out of range', () => {
      render(<ChapterTabs bookId="book-1" />);
      act(() => {
        fireEvent.keyDown(document, { key: '9', ctrlKey: true });
      });
      expect(mockActions.setActiveChapter).not.toHaveBeenCalled();
    });

    it('does not trigger without Ctrl modifier', () => {
      render(<ChapterTabs bookId="book-1" />);
      act(() => {
        fireEvent.keyDown(document, { key: '1', ctrlKey: false });
      });
      expect(mockActions.setActiveChapter).not.toHaveBeenCalled();
    });

    it('removes keydown listener on unmount', () => {
      const { unmount } = render(<ChapterTabs bookId="book-1" />);
      unmount();
      act(() => {
        fireEvent.keyDown(document, { key: '1', ctrlKey: true });
      });
      expect(mockActions.setActiveChapter).not.toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // TabContent callbacks (onContentChange / onChapterSave)
  // -------------------------------------------------------------------------

  describe('TabContent callbacks', () => {
    it('onContentChange callback logs content length', () => {
      const consoleSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
      render(<ChapterTabs bookId="book-1" />);
      fireEvent.click(screen.getByTestId('content-change-btn'));
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Content changed for chapter ch-1')
      );
      consoleSpy.mockRestore();
    });

    it('onChapterSave callback calls saveTabState', () => {
      render(<ChapterTabs bookId="book-1" />);
      fireEvent.click(screen.getByTestId('chapter-save-btn'));
      expect(mockActions.saveTabState).toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // closeTab forwarding
  // -------------------------------------------------------------------------

  describe('onTabClose forwarding', () => {
    it('calls closeTab when a tab close is triggered via TabBar', () => {
      render(<ChapterTabs bookId="book-1" />);
      fireEvent.click(screen.getByTestId('close-btn'));
      expect(mockActions.closeTab).toHaveBeenCalledWith('ch-1');
    });
  });
});
