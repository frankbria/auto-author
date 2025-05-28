
import { ChapterTabMetadata, ChapterStatus } from '@/types/chapter-tabs';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ChaptersMetadataResponse {
  book_id: string;
  chapters: ChapterTabMetadata[];
  total_chapters: number;
  completion_stats: {
    draft: number;
    in_progress: number;
    completed: number;
    published: number;
  };
  last_active_chapter?: string;
}

interface TabState {
  active_chapter_id: string | null;
  open_tab_ids: string[];
  tab_order: string[];
  session_id?: string;
}

class ChapterTabsAPI {
  private async fetch(endpoint: string, options: RequestInit = {}) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  async getChaptersMetadata(bookId: string, includeContentStats = true): Promise<ChaptersMetadataResponse> {
    return this.fetch(`/api/v1/books/${bookId}/chapters/metadata?include_content_stats=${includeContentStats}`);
  }

  async updateChapterStatus(bookId: string, chapterId: string, status: ChapterStatus): Promise<void> {
    return this.fetch(`/api/v1/books/${bookId}/chapters/bulk-status`, {
      method: 'PATCH',
      body: JSON.stringify({
        chapter_ids: [chapterId],
        status,
        update_timestamp: true
      })
    });
  }

  async updateBulkChapterStatus(bookId: string, chapterIds: string[], status: ChapterStatus): Promise<void> {
    return this.fetch(`/api/v1/books/${bookId}/chapters/bulk-status`, {
      method: 'PATCH',
      body: JSON.stringify({
        chapter_ids: chapterIds,
        status,
        update_timestamp: true
      })
    });
  }
  async getChapterContent(bookId: string, chapterId: string): Promise<string> {
    const response = await this.fetch(`/api/v1/books/${bookId}/chapters/${chapterId}/content?include_metadata=true&track_access=true`);
    return response.content || '';
  }

  async saveTabState(bookId: string, tabState: Omit<TabState, 'session_id'>): Promise<void> {
    const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    return this.fetch(`/api/v1/books/${bookId}/chapters/tab-state`, {
      method: 'POST',
      body: JSON.stringify({
        ...tabState,
        session_id: sessionId
      })
    });
  }

  async getTabState(bookId: string, sessionId?: string): Promise<TabState | null> {
    const params = sessionId ? `?session_id=${sessionId}` : '';
    return this.fetch(`/api/v1/books/${bookId}/chapters/tab-state${params}`);
  }
}

export const chapterTabsApi = new ChapterTabsAPI();