
// src/lib/cache/chapter-content-cache.ts
class ChapterContentCache {
    private cache = new Map<string, { content: string; timestamp: number }>();
    private readonly TTL = 5 * 60 * 1000; // 5 minutes
  
    set(key: string, content: string) {
      this.cache.set(key, { content, timestamp: Date.now() });
    }
  
    get(key: string): string | null {
      const cached = this.cache.get(key);
      if (!cached) return null;
  
      if (Date.now() - cached.timestamp > this.TTL) {
        this.cache.delete(key);
        return null;
      }
  
      return cached.content;
    }
  
    clear() {
      this.cache.clear();
    }
  }
  
  export const chapterContentCache = new ChapterContentCache();