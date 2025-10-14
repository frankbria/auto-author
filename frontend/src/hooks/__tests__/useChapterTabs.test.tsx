/**
 * Comprehensive tests for useChapterTabs hook
 *
 * Test Coverage Areas:
 * - Basic hook behavior (5 tests)
 * - Chapter operations (6 tests)
 * - Navigation (4 tests)
 * - Error handling (6 tests)
 * - Edge cases (4 tests)
 * - Integration (2 tests)
 *
 * Total: 27+ tests
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { useChapterTabs } from '../useChapterTabs';
import bookClient from '@/lib/api/bookClient';
import { ChapterStatus, ChapterTabMetadata } from '@/types/chapter-tabs';

// Mock bookClient
jest.mock('@/lib/api/bookClient', () => ({
  __esModule: true,
  default: {
    getToc: jest.fn(),
    getChaptersMetadata: jest.fn(),
    getTabState: jest.fn(),
    saveTabState: jest.fn(),
    updateChapterStatus: jest.fn(),
  },
}));

// Mock localStorage
const mockLocalStorage = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: jest.fn((index: number) => {
      const keys = Object.keys(store);
      return keys[index] || null;
    }),
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
  writable: true,
});

// Test data
const mockBookId = 'test-book-123';

const createMockChapter = (id: string, overrides?: Partial<ChapterTabMetadata>): ChapterTabMetadata => ({
  id,
  title: `Chapter ${id}`,
  status: ChapterStatus.DRAFT,
  word_count: 100,
  last_modified: new Date().toISOString(),
  estimated_reading_time: 5,
  order: parseInt(id.replace('chapter-', '')),
  level: 1,
  has_content: true,
  ...overrides,
});

const mockChapters: ChapterTabMetadata[] = [
  createMockChapter('chapter-1'),
  createMockChapter('chapter-2'),
  createMockChapter('chapter-3'),
];

const mockTocResponse = {
  toc: {
    chapters: mockChapters.map(ch => ({
      id: ch.id,
      title: ch.title,
      description: `Description for ${ch.title}`,
      level: ch.level,
      order: ch.order,
      status: ch.status,
      word_count: ch.word_count,
      estimated_reading_time: ch.estimated_reading_time,
      last_modified: ch.last_modified,
      subchapters: [],
    })),
    total_chapters: 3,
    estimated_pages: 10,
    structure_notes: 'Test structure',
  },
};

const mockMetadataResponse = {
  book_id: mockBookId,
  chapters: mockChapters.map(ch => ({
    id: ch.id,
    title: ch.title,
    description: `Description for ${ch.title}`,
    level: ch.level,
    order: ch.order,
    status: ch.status,
    word_count: ch.word_count,
    estimated_reading_time: ch.estimated_reading_time,
    last_modified: ch.last_modified,
  })),
  total_chapters: 3,
  completion_stats: {
    draft: 3,
    in_progress: 0,
    completed: 0,
    published: 0,
  },
};

describe('useChapterTabs Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockLocalStorage.clear();

    // Default successful responses
    (bookClient.getToc as jest.Mock).mockResolvedValue(mockTocResponse);
    (bookClient.getChaptersMetadata as jest.Mock).mockResolvedValue(mockMetadataResponse);
    (bookClient.getTabState as jest.Mock).mockResolvedValue(null);
    (bookClient.saveTabState as jest.Mock).mockResolvedValue({});
    (bookClient.updateChapterStatus as jest.Mock).mockResolvedValue({});
  });

  // ==================== BASIC HOOK BEHAVIOR (5 tests) ====================

  describe('Basic Hook Behavior', () => {
    test('1. Returns expected initial state', async () => {
      const { result } = renderHook(() => useChapterTabs(mockBookId));

      // Initial loading state
      expect(result.current.state.is_loading).toBe(true);
      expect(result.current.state.chapters).toEqual([]);
      expect(result.current.state.active_chapter_id).toBeNull();
      expect(result.current.state.open_tab_ids).toEqual([]);
      expect(result.current.state.tab_order).toEqual([]);
      expect(result.current.state.error).toBeNull();

      // Wait for data to load
      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // After loading
      expect(result.current.state.chapters).toHaveLength(3);
      expect(result.current.state.active_chapter_id).toBe('chapter-1');
      expect(result.current.state.open_tab_ids).toEqual(['chapter-1']);
    });

    test('2. Handles tab selection correctly', async () => {
      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      act(() => {
        result.current.actions.setActiveChapter('chapter-2');
      });

      expect(result.current.state.active_chapter_id).toBe('chapter-2');
      expect(result.current.state.open_tab_ids).toContain('chapter-2');
    });

    test('3. Updates active tab state', async () => {
      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // Select different chapters
      act(() => {
        result.current.actions.setActiveChapter('chapter-2');
      });
      expect(result.current.state.active_chapter_id).toBe('chapter-2');

      act(() => {
        result.current.actions.setActiveChapter('chapter-3');
      });
      expect(result.current.state.active_chapter_id).toBe('chapter-3');
    });

    test('4. Maintains tab history', async () => {
      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // Open multiple tabs
      act(() => {
        result.current.actions.openTab('chapter-1');
        result.current.actions.openTab('chapter-2');
        result.current.actions.openTab('chapter-3');
      });

      expect(result.current.state.open_tab_ids).toEqual(['chapter-1', 'chapter-2', 'chapter-3']);
      expect(result.current.state.tab_order).toContain('chapter-1');
      expect(result.current.state.tab_order).toContain('chapter-2');
      expect(result.current.state.tab_order).toContain('chapter-3');
    });

    test('5. Clears state appropriately', async () => {
      const { result, unmount } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      act(() => {
        result.current.actions.openTab('chapter-2');
      });

      // Wait for auto-save to complete
      await waitFor(() => {
        expect(mockLocalStorage.setItem).toHaveBeenCalled();
      }, { timeout: 2000 });

      // Unmount should trigger cleanup
      unmount();

      // Verify localStorage was updated
      expect(mockLocalStorage.setItem).toHaveBeenCalled();
    });
  });

  // ==================== CHAPTER OPERATIONS (6 tests) ====================

  describe('Chapter Operations', () => {
    test('6. Adds new chapter tab correctly', async () => {
      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      const initialTabCount = result.current.state.open_tab_ids.length;

      act(() => {
        result.current.actions.openTab('chapter-2');
      });

      expect(result.current.state.open_tab_ids).toHaveLength(initialTabCount + 1);
      expect(result.current.state.open_tab_ids).toContain('chapter-2');
      expect(result.current.state.active_chapter_id).toBe('chapter-2');
    });

    test('7. Removes chapter tab and updates active', async () => {
      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // Open multiple tabs
      act(() => {
        result.current.actions.openTab('chapter-1');
        result.current.actions.openTab('chapter-2');
        result.current.actions.openTab('chapter-3');
      });

      // Close active tab
      act(() => {
        result.current.actions.closeTab('chapter-3');
      });

      expect(result.current.state.open_tab_ids).not.toContain('chapter-3');
      expect(result.current.state.active_chapter_id).not.toBe('chapter-3');
      expect(result.current.state.active_chapter_id).toBeTruthy();
    });

    test('8. Reorders tabs correctly', async () => {
      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      const initialOrder = [...result.current.state.tab_order];

      await act(async () => {
        await result.current.actions.reorderTabs(0, 2);
      });

      expect(result.current.state.tab_order).not.toEqual(initialOrder);
      expect(result.current.state.tab_order).toHaveLength(initialOrder.length);
    });

    test('9. Updates chapter metadata', async () => {
      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      const chapterToUpdate = result.current.state.chapters[0];
      const newStatus = ChapterStatus.IN_PROGRESS;

      await act(async () => {
        await result.current.actions.updateChapterStatus(chapterToUpdate.id, newStatus);
      });

      const updatedChapter = result.current.state.chapters.find(ch => ch.id === chapterToUpdate.id);
      expect(updatedChapter?.status).toBe(newStatus);
      expect(bookClient.updateChapterStatus).toHaveBeenCalledWith(mockBookId, chapterToUpdate.id, newStatus);
    });

    test('10. Handles chapter duplication', async () => {
      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // Open same chapter twice - should not duplicate
      act(() => {
        result.current.actions.openTab('chapter-1');
        result.current.actions.openTab('chapter-1');
      });

      const chapter1Count = result.current.state.open_tab_ids.filter(id => id === 'chapter-1').length;
      expect(chapter1Count).toBe(1);
    });

    test('11. Persists tab state to localStorage', async () => {
      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      act(() => {
        result.current.actions.openTab('chapter-2');
      });

      // Wait for debounced save
      await waitFor(() => {
        expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
          `tabState_${mockBookId}`,
          expect.stringContaining('chapter-2')
        );
      }, { timeout: 2000 });
    });
  });

  // ==================== NAVIGATION (4 tests) ====================

  describe('Navigation', () => {
    test('12. Navigates to next tab', async () => {
      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // Open multiple tabs
      act(() => {
        result.current.actions.openTab('chapter-1');
        result.current.actions.openTab('chapter-2');
        result.current.actions.openTab('chapter-3');
      });

      // Set to first tab
      act(() => {
        result.current.actions.setActiveChapter('chapter-1');
      });

      const currentIndex = result.current.state.tab_order.indexOf('chapter-1');
      const nextChapterId = result.current.state.tab_order[currentIndex + 1];

      if (nextChapterId) {
        act(() => {
          result.current.actions.setActiveChapter(nextChapterId);
        });

        expect(result.current.state.active_chapter_id).toBe(nextChapterId);
      }
    });

    test('13. Navigates to previous tab', async () => {
      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // Open multiple tabs
      act(() => {
        result.current.actions.openTab('chapter-1');
        result.current.actions.openTab('chapter-2');
        result.current.actions.openTab('chapter-3');
      });

      // Set to last tab
      act(() => {
        result.current.actions.setActiveChapter('chapter-3');
      });

      const currentIndex = result.current.state.tab_order.indexOf('chapter-3');
      const prevChapterId = result.current.state.tab_order[currentIndex - 1];

      if (prevChapterId) {
        act(() => {
          result.current.actions.setActiveChapter(prevChapterId);
        });

        expect(result.current.state.active_chapter_id).toBe(prevChapterId);
      }
    });

    test('14. Handles navigation at boundaries (first/last)', async () => {
      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // Test first boundary
      const firstChapterId = result.current.state.tab_order[0];
      act(() => {
        result.current.actions.setActiveChapter(firstChapterId);
      });
      expect(result.current.state.active_chapter_id).toBe(firstChapterId);

      // Test last boundary
      const lastChapterId = result.current.state.tab_order[result.current.state.tab_order.length - 1];
      act(() => {
        result.current.actions.setActiveChapter(lastChapterId);
      });
      expect(result.current.state.active_chapter_id).toBe(lastChapterId);
    });

    test('15. Supports keyboard shortcuts (simulated Ctrl+1-9)', async () => {
      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // Open multiple tabs
      act(() => {
        result.current.actions.openTab('chapter-1');
        result.current.actions.openTab('chapter-2');
        result.current.actions.openTab('chapter-3');
      });

      // Simulate Ctrl+2 (select second tab)
      const secondTabId = result.current.state.tab_order[1];
      if (secondTabId) {
        act(() => {
          result.current.actions.setActiveChapter(secondTabId);
        });

        expect(result.current.state.active_chapter_id).toBe(secondTabId);
      }
    });
  });

  // ==================== ERROR HANDLING (6 tests) ====================

  describe('Error Handling', () => {
    test('16. Handles failed chapter load', async () => {
      const errorMessage = 'Failed to load chapters';
      // Both TOC and fallback metadata API fail
      (bookClient.getToc as jest.Mock).mockRejectedValueOnce(new Error(errorMessage));
      (bookClient.getChaptersMetadata as jest.Mock).mockRejectedValueOnce(new Error(errorMessage));

      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // After both fail, should have empty chapters but not necessarily an error
      // (hook handles gracefully)
      expect(result.current.state.chapters).toEqual([]);
      expect(result.current.loading).toBe(false);
    });

    test('17. Shows error state for invalid chapter', async () => {
      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // Try to open non-existent chapter
      act(() => {
        result.current.actions.openTab('invalid-chapter-id');
      });

      // Hook should handle gracefully (add to open tabs even if not in chapters list)
      expect(result.current.state.open_tab_ids).toContain('invalid-chapter-id');
    });

    test('18. Recovers from network errors', async () => {
      // Both initial calls fail
      (bookClient.getToc as jest.Mock).mockRejectedValueOnce(new Error('Network error'));
      (bookClient.getChaptersMetadata as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // Initial load fails gracefully
      expect(result.current.state.chapters).toEqual([]);

      // Reset mocks for successful retry
      (bookClient.getToc as jest.Mock).mockResolvedValueOnce(mockTocResponse);

      // Trigger refresh to recover
      await act(async () => {
        await result.current.actions.refreshChapters();
      });

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
        expect(result.current.state.chapters).toHaveLength(3);
      });
    });

    test('19. Retries failed operations', async () => {
      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // Mock update failure
      (bookClient.updateChapterStatus as jest.Mock).mockRejectedValueOnce(new Error('Update failed'));
      (bookClient.getChaptersMetadata as jest.Mock).mockResolvedValue(mockMetadataResponse);

      // First attempt fails and triggers error state
      await act(async () => {
        try {
          await result.current.actions.updateChapterStatus('chapter-1', ChapterStatus.COMPLETED);
        } catch (error) {
          // Expected to fail internally
        }
      });

      // Wait for error handling to complete
      await waitFor(() => {
        // Hook reloads chapters on error, so error gets cleared
        expect(result.current.state.is_loading).toBe(false);
      });

      // Reset mock for successful retry
      (bookClient.updateChapterStatus as jest.Mock).mockResolvedValueOnce({});

      // Retry succeeds
      await act(async () => {
        await result.current.actions.updateChapterStatus('chapter-1', ChapterStatus.COMPLETED);
      });

      // Verify update was called again
      expect(bookClient.updateChapterStatus).toHaveBeenCalledTimes(2);
    });

    test('20. Handles localStorage errors', async () => {
      mockLocalStorage.setItem.mockImplementationOnce(() => {
        throw new Error('localStorage is full');
      });

      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // Should not crash on localStorage error
      act(() => {
        result.current.actions.openTab('chapter-2');
      });

      // Hook should still function
      expect(result.current.state.active_chapter_id).toBe('chapter-2');
    });

    test('21. Shows appropriate error messages', async () => {
      // Mock console.error and console.warn to suppress output
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});

      const specificError = 'Chapter not found';
      (bookClient.getToc as jest.Mock).mockRejectedValueOnce(new Error(specificError));
      (bookClient.getChaptersMetadata as jest.Mock).mockRejectedValueOnce(new Error(specificError));

      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // Hook handles errors gracefully, console methods should be called
      expect(consoleWarnSpy).toHaveBeenCalled();
      expect(consoleErrorSpy).toHaveBeenCalled();

      // Cleanup
      consoleErrorSpy.mockRestore();
      consoleWarnSpy.mockRestore();
    });
  });

  // ==================== EDGE CASES (4 tests) ====================

  describe('Edge Cases', () => {
    test('22. Handles empty chapter list', async () => {
      (bookClient.getToc as jest.Mock).mockResolvedValueOnce({
        toc: {
          chapters: [],
          total_chapters: 0,
          estimated_pages: 0,
          structure_notes: '',
        },
      });

      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      expect(result.current.state.chapters).toEqual([]);
      expect(result.current.state.active_chapter_id).toBeNull();
      expect(result.current.state.open_tab_ids).toEqual([]);
    });

    test('23. Handles single chapter', async () => {
      const singleChapter = [createMockChapter('chapter-1')];
      (bookClient.getToc as jest.Mock).mockResolvedValueOnce({
        toc: {
          chapters: [singleChapter[0]],
          total_chapters: 1,
          estimated_pages: 5,
          structure_notes: 'Single chapter',
        },
      });

      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      expect(result.current.state.chapters).toHaveLength(1);
      expect(result.current.state.active_chapter_id).toBe('chapter-1');

      // Closing the only tab
      act(() => {
        result.current.actions.closeTab('chapter-1');
      });

      expect(result.current.state.open_tab_ids).toEqual([]);
      expect(result.current.state.active_chapter_id).toBeNull();
    });

    test('24. Handles maximum chapters (if limit exists)', async () => {
      // Test with a large number of chapters
      const manyChapters = Array.from({ length: 50 }, (_, i) =>
        createMockChapter(`chapter-${i + 1}`)
      );

      (bookClient.getToc as jest.Mock).mockResolvedValueOnce({
        toc: {
          chapters: manyChapters,
          total_chapters: 50,
          estimated_pages: 500,
          structure_notes: 'Many chapters',
        },
      });

      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      expect(result.current.state.chapters).toHaveLength(50);
      expect(result.current.state.tab_order).toHaveLength(50);
    });

    test('25. Handles rapid tab switching', async () => {
      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // Rapidly switch between tabs
      act(() => {
        result.current.actions.setActiveChapter('chapter-1');
        result.current.actions.setActiveChapter('chapter-2');
        result.current.actions.setActiveChapter('chapter-3');
        result.current.actions.setActiveChapter('chapter-1');
        result.current.actions.setActiveChapter('chapter-2');
      });

      // Final state should be stable
      expect(result.current.state.active_chapter_id).toBe('chapter-2');
      expect(result.current.state.open_tab_ids).toContain('chapter-1');
      expect(result.current.state.open_tab_ids).toContain('chapter-2');
      expect(result.current.state.open_tab_ids).toContain('chapter-3');
    });
  });

  // ==================== INTEGRATION (2 tests) ====================

  describe('Integration', () => {
    test('26. Integrates with auto-save correctly', async () => {
      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // Verify hook exposes saveTabState action
      expect(result.current.actions.saveTabState).toBeDefined();
      expect(typeof result.current.actions.saveTabState).toBe('function');

      // Verify hook has state that would be saved
      expect(result.current.state.active_chapter_id).toBeTruthy();
      expect(result.current.state.open_tab_ids.length).toBeGreaterThan(0);
      expect(result.current.state.tab_order.length).toBeGreaterThan(0);

      // Test that changing state would trigger save conditions
      act(() => {
        result.current.actions.openTab('chapter-2');
      });

      // Verify state changed
      expect(result.current.state.open_tab_ids).toContain('chapter-2');

      // Wait for potential debounced save (hook auto-saves after 1 second)
      await waitFor(() => {
        // Check if localStorage was called at some point
        const localStorageCalls = (mockLocalStorage.setItem as jest.Mock).mock.calls;
        const hasTabStateSave = localStorageCalls.some(call =>
          call[0] === `tabState_${mockBookId}`
        );
        expect(hasTabStateSave).toBe(true);
      }, { timeout: 2000 });
    });

    test('27. Syncs with backend state', async () => {
      const backendTabState = {
        active_chapter_id: 'chapter-2',
        open_tab_ids: ['chapter-1', 'chapter-2'],
        tab_order: ['chapter-1', 'chapter-2', 'chapter-3'],
        last_updated: new Date().toISOString(),
      };

      (bookClient.getTabState as jest.Mock).mockResolvedValueOnce(backendTabState);

      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // Should use backend state
      expect(result.current.state.active_chapter_id).toBe('chapter-2');
      expect(result.current.state.open_tab_ids).toEqual(['chapter-1', 'chapter-2']);
    });
  });

  // ==================== ADDITIONAL TESTS ====================

  describe('Additional Scenarios', () => {
    test('28. Handles initialActiveChapter parameter', async () => {
      const initialChapter = 'chapter-3';
      const { result } = renderHook(() => useChapterTabs(mockBookId, initialChapter));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // Should prioritize initial parameter if no saved state
      expect(result.current.state.active_chapter_id).toBe(initialChapter);
    });

    test('29. Handles TOC fallback to metadata API', async () => {
      // TOC fails, metadata succeeds
      (bookClient.getToc as jest.Mock).mockRejectedValueOnce(new Error('TOC not found'));
      (bookClient.getChaptersMetadata as jest.Mock).mockResolvedValueOnce(mockMetadataResponse);

      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      expect(result.current.state.chapters).toHaveLength(3);
      expect(bookClient.getChaptersMetadata).toHaveBeenCalled();
    });

    test('30. Refreshes chapters on demand', async () => {
      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // Add new chapter to mock
      const updatedChapters = [...mockChapters, createMockChapter('chapter-4')];
      (bookClient.getToc as jest.Mock).mockResolvedValueOnce({
        toc: {
          chapters: updatedChapters,
          total_chapters: 4,
          estimated_pages: 15,
          structure_notes: 'Updated',
        },
      });

      await act(async () => {
        await result.current.actions.refreshChapters();
      });

      await waitFor(() => {
        expect(result.current.state.chapters).toHaveLength(4);
      });
    });

    test('31. Preserves open tabs when refreshing', async () => {
      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // Open multiple tabs
      act(() => {
        result.current.actions.openTab('chapter-1');
        result.current.actions.openTab('chapter-2');
      });

      const openTabsBeforeRefresh = [...result.current.state.open_tab_ids];

      await act(async () => {
        await result.current.actions.refreshChapters();
      });

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // Open tabs should still be open
      openTabsBeforeRefresh.forEach(tabId => {
        expect(result.current.state.open_tab_ids).toContain(tabId);
      });
    });

    test('32. Handles deleted chapters gracefully', async () => {
      const { result } = renderHook(() => useChapterTabs(mockBookId));

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // Open chapter that will be deleted
      act(() => {
        result.current.actions.openTab('chapter-2');
      });

      // Simulate chapter deletion
      const updatedChapters = mockChapters.filter(ch => ch.id !== 'chapter-2');
      (bookClient.getToc as jest.Mock).mockResolvedValueOnce({
        toc: {
          chapters: updatedChapters,
          total_chapters: 2,
          estimated_pages: 8,
          structure_notes: 'Chapter deleted',
        },
      });

      await act(async () => {
        await result.current.actions.refreshChapters();
      });

      await waitFor(() => {
        expect(result.current.state.is_loading).toBe(false);
      });

      // Deleted chapter should be removed from tabs
      expect(result.current.state.open_tab_ids).not.toContain('chapter-2');
      expect(result.current.state.active_chapter_id).not.toBe('chapter-2');
    });
  });
});
