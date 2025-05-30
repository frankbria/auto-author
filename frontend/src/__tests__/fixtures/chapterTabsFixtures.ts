import { ChapterStatus, ChapterTabMetadata } from '@/types/chapter-tabs';

export const createMockChapter = (id: string, title: string, overrides = {}): ChapterTabMetadata => ({
  id,
  title,
  status: ChapterStatus.DRAFT,
  last_modified: new Date().toISOString(),
  word_count: 1000,
  estimated_reading_time: 5,
  has_content: true,
  level: 1,
  order: 1,
  ...overrides
});

export const generateChaptersFixture = (count: number) => {
  const chapters = [];
  const tabOrder = [];
  
  for (let i = 1; i <= count; i++) {
    const id = `ch-${i}`;
    const status = i <= 2 ? ChapterStatus.DRAFT : 
                   i <= 4 ? ChapterStatus.IN_PROGRESS : 
                   ChapterStatus.COMPLETED;
    
    chapters.push(createMockChapter(id, `Chapter ${i}`, {
      status,
      word_count: i * 150,
      estimated_reading_time: Math.ceil(i * 150 / 200),
      order: i
    }));
    tabOrder.push(id);
  }
  
  return { chapters, tabOrder };
};

export const mockChapterTabsState = (overrides = {}) => ({
  state: {
    chapters: [createMockChapter('1', 'Chapter 1')],
    active_chapter_id: '1',
    tab_order: ['1'],
    unsaved_changes: {},
    is_loading: false,
    error: null,
    ...overrides
  },
  actions: {
    setActiveChapter: jest.fn(),
    reorderTabs: jest.fn(),
    closeTab: jest.fn(),
    updateChapterStatus: jest.fn(),
    saveTabState: jest.fn(),
    refreshChapters: jest.fn()
  },
  loading: false,
  error: null
});

// Mock localStorage
export const mockLocalStorage = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value.toString();
    }),
    clear: jest.fn(() => {
      store = {};
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    getAll: () => store,
  };
})();

// Setup for each test
export const setupTestEnvironment = () => {
  Object.defineProperty(window, 'localStorage', {
    value: mockLocalStorage,
  });
  
  // Mock IntersectionObserver
  window.IntersectionObserver = jest.fn().mockImplementation(() => ({
    observe: jest.fn(),
    unobserve: jest.fn(),
    disconnect: jest.fn(),
  }));
  
  // Mock ResizeObserver
  window.ResizeObserver = jest.fn().mockImplementation(() => ({
    observe: jest.fn(),
    unobserve: jest.fn(),
    disconnect: jest.fn(),
  }));
};
