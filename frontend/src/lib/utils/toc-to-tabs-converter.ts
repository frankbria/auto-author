// Helper utility to convert between TOC structures and ChapterTabMetadata formats
import { ChapterTabMetadata, ChapterStatus } from '@/types/chapter-tabs';

// Interface for any TOC structure that can be converted to chapter tabs
interface ConvertibleToc {
  chapters: Array<{
    id: string;
    title: string;
    level: number;
    order: number;
    status?: ChapterStatus;
    word_count?: number;
    last_modified?: string;
    estimated_reading_time?: number;
    content_id?: string;
    subchapters: Array<{
      id: string;
      title: string;
      level: number;
      order: number;
    }>;
  }>;
}

// Flattens a hierarchical TOC structure into a flat list of chapters with proper metadata
export function convertTocToChapterTabs(tocData: ConvertibleToc | null): ChapterTabMetadata[] {
  if (!tocData || !tocData.chapters) {
    return [];
  }

  const chapterTabs: ChapterTabMetadata[] = [];
  
  // Process main chapters
  tocData.chapters.forEach((chapter) => {
    chapterTabs.push(convertChapterToTab(chapter));
    
    // Process subchapters if they exist
    if (chapter.subchapters && chapter.subchapters.length > 0) {
      chapter.subchapters.forEach((subchapter) => {
        // Convert subchapter to tab with proper metadata
        chapterTabs.push({
          id: subchapter.id,
          title: subchapter.title,
          status: ChapterStatus.DRAFT, // Default status for subchapters
          word_count: 0, // Default word count
          last_modified: new Date().toISOString(),
          estimated_reading_time: 0,
          order: subchapter.order,
          level: subchapter.level,
          has_content: false,
        });
      });
    }
  });
  
  return chapterTabs;
}

// Converts a single chapter object from any TOC structure to ChapterTabMetadata
function convertChapterToTab(chapter: ConvertibleToc['chapters'][0]): ChapterTabMetadata {
  return {
    id: chapter.id,
    title: chapter.title,
    status: chapter.status || ChapterStatus.DRAFT,
    word_count: chapter.word_count || 0,
    last_modified: chapter.last_modified || new Date().toISOString(),
    estimated_reading_time: chapter.estimated_reading_time || 0,
    order: chapter.order,
    level: chapter.level,
    has_content: Boolean(chapter.content_id),
  };
}

// Determines if a chapter has a parent in the TOC structure
export function hasParentChapter(chapterId: string, tocData: ConvertibleToc | null): boolean {
  if (!tocData || !tocData.chapters) {
    return false;
  }

  for (const chapter of tocData.chapters) {
    if (chapter.subchapters && chapter.subchapters.some(sub => sub.id === chapterId)) {
      return true;
    }
  }

  return false;
}

// Gets parent chapter ID for a given subchapter
export function getParentChapterId(chapterId: string, tocData: ConvertibleToc | null): string | null {
  if (!tocData || !tocData.chapters) {
    return null;
  }

  for (const chapter of tocData.chapters) {
    if (chapter.subchapters && chapter.subchapters.some(sub => sub.id === chapterId)) {
      return chapter.id;
    }
  }

  return null;
}
