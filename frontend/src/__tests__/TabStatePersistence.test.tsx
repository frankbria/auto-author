import { renderHook, act, waitFor } from '@testing-library/react';
import { useChapterTabs } from '@/hooks/useChapterTabs';
import bookClient from '@/lib/api/bookClient';
import { mockLocalStorage, setupTestEnvironment } from './fixtures/chapterTabsFixtures';

// Mock the API client
jest.mock('@/lib/api/bookClient', () => ({
  __esModule: true,
  default: {
    getTabState: jest.fn(),
    saveTabState: jest.fn(),
    getChaptersMetadata: jest.fn(),
    getToc: jest.fn(),
    setAuthToken: jest.fn(),
  },
}));

describe('Tab State Persistence', () => {
  const bookId = 'test-book-id';
  const mockChapters = [
    { 
      id: 'ch1', 
      title: 'Chapter 1', 
      status: 'draft',
      word_count: 1000,
      estimated_reading_time: 5,
      has_content: true,
      level: 1,
      order: 1,
      last_modified: new Date().toISOString()
    },
    { 
      id: 'ch2', 
      title: 'Chapter 2', 
      status: 'in_progress',
      word_count: 1500,
      estimated_reading_time: 8,
      has_content: true,
      level: 1,
      order: 2,
      last_modified: new Date().toISOString()
    },
    { 
      id: 'ch3', 
      title: 'Chapter 3', 
      status: 'completed',
      word_count: 2000,
      estimated_reading_time: 10,
      has_content: true,
      level: 1,
      order: 3,
      last_modified: new Date().toISOString()
    },
  ];
  
  beforeEach(() => {
    setupTestEnvironment();
    jest.clearAllMocks();
    mockLocalStorage.clear();
    
    // Mock API responses
    (bookClient.getTabState as jest.Mock).mockResolvedValue({
      tab_state: {
        active_chapter_id: 'ch2',
        open_tab_ids: ['ch1', 'ch2', 'ch3'],
        tab_order: ['ch1', 'ch2', 'ch3'],
        last_updated: new Date().toISOString()
      }
    });
    
    (bookClient.getChaptersMetadata as jest.Mock).mockResolvedValue({
      chapters: mockChapters,
    });
    
    (bookClient.getToc as jest.Mock).mockResolvedValue({
      toc: {
        chapters: mockChapters,
        total_chapters: mockChapters.length,
        estimated_pages: 23,
        status: "edited",
        version: 1,
        generated_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
    });

    (bookClient.saveTabState as jest.Mock).mockResolvedValue({ success: true });
  });
  
  test('restores tab state from localStorage on initial load', async () => {
    // Setup localStorage with saved state
    const savedState = {
      active_chapter_id: 'ch3',
      open_tab_ids: ['ch2', 'ch3'],
      tab_order: ['ch2', 'ch3'],
      last_updated: new Date().toISOString()
    };
    mockLocalStorage.setItem(`tabState_${bookId}`, JSON.stringify(savedState));
    
    // Render the hook
    const { result } = renderHook(() => useChapterTabs(bookId));
    
    // Wait for async operations
    await waitFor(() => {
      expect(result.current.state.active_chapter_id).toBe(savedState.active_chapter_id);
    });
    
    expect(result.current.state.tab_order).toEqual(savedState.tab_order);
    
    // Verify localStorage was checked
    expect(mockLocalStorage.getItem).toHaveBeenCalledWith(`tabState_${bookId}`);
  });
  
  test('saves tab state to localStorage and backend on state changes', async () => {
    const { result } = renderHook(() => useChapterTabs(bookId));
    
    // Wait for initial load
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    
    // Change active chapter
    act(() => {
      result.current.actions.setActiveChapter('ch2');
    });
    
    await waitFor(() => {
      // Verify localStorage was updated
      expect(mockLocalStorage.setItem).toHaveBeenCalled();
      
      // Verify API was called to save state
      expect(bookClient.saveTabState).toHaveBeenCalledWith(
        bookId, 
        expect.objectContaining({
          active_chapter_id: 'ch2',
        })
      );
    });
  });
  
  test('prefers backend state over localStorage when backend is newer', async () => {
    // Setup localStorage with older state
    const localState = {
      active_chapter_id: 'ch1',
      open_tab_ids: ['ch1'],
      tab_order: ['ch1'],
      last_updated: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
    };
    mockLocalStorage.setItem(`tabState_${bookId}`, JSON.stringify(localState));
    
    // Mock backend response with newer state
    const backendState = {
      tab_state: {
        active_chapter_id: 'ch3',
        open_tab_ids: ['ch1', 'ch3'],
        tab_order: ['ch1', 'ch3'],
        last_updated: new Date().toISOString(), // now
      }
    };
    (bookClient.getTabState as jest.Mock).mockResolvedValue(backendState);
    
    // Render the hook
    const { result } = renderHook(() => useChapterTabs(bookId));
    
    // Wait for async operations
    await waitFor(() => {
      expect(result.current.state.active_chapter_id).toBe(backendState.tab_state.active_chapter_id);
    });
    
    expect(result.current.state.tab_order).toEqual(backendState.tab_state.tab_order);
  });
  
  test('handles offline mode gracefully', async () => {
    // Mock API failure
    (bookClient.getTabState as jest.Mock).mockRejectedValue(new Error('Network error'));
    (bookClient.saveTabState as jest.Mock).mockRejectedValue(new Error('Network error'));
    
    // Setup localStorage with fallback state
    const localState = {
      active_chapter_id: 'ch2',
      open_tab_ids: ['ch1', 'ch2'],
      tab_order: ['ch1', 'ch2'],
      last_updated: new Date().toISOString()
    };
    mockLocalStorage.setItem(`tabState_${bookId}`, JSON.stringify(localState));
    
    const { result } = renderHook(() => useChapterTabs(bookId));
    
    // Should still be able to load chapters from TOC or metadata
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    
    // State changes should still work locally
    act(() => {
      result.current.actions.setActiveChapter('ch1');
    });
    
    expect(result.current.state.active_chapter_id).toBe('ch1');
  });
});
