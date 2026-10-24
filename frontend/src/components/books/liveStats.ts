import { calculateBookProgress, ChapterStatus } from '@/types/book';
import type { ChapterTabMetadata } from '@/types/chapter-tabs';

type Stats = { chapters: { wordCount: number; completed: boolean }[]; progress: number };

/** Book Stats from the tabs' chapter list; the loaded book's until the tabs report (#1092). */
export function liveStats(live: ChapterTabMetadata[] | null, book: Stats): Stats {
  if (!live) return book;
  return {
    chapters: live.map((c) => ({
      wordCount: c.word_count,
      completed: c.status === ChapterStatus.COMPLETED || c.status === ChapterStatus.PUBLISHED,
    })),
    progress: calculateBookProgress({ toc_items: live }),
  };
}
