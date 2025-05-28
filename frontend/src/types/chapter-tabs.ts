// Enhanced types for Chapter Tabs functionality
export interface ChapterTabMetadata {
  id: string;
  title: string;
  status: ChapterStatus;
  word_count: number;
  last_modified: string;
  estimated_reading_time: number;
  order: number;
  level: number;
  has_content: boolean;
  has_unsaved_changes?: boolean;
  is_loading?: boolean;
  error?: string;
  content?: string; // Optional field added
}

export interface ChapterTabsState {
  chapters: ChapterTabMetadata[];
  active_chapter_id: string | null;
  open_tab_ids: string[];
  tab_order: string[];
  is_loading: boolean;
  error: string | null;
  last_active_chapter?: string;
}

export interface TabContextMenuAction {
  id: string;
  label: string;
  icon?: string;
  onClick: (chapterId: string) => void;
  disabled?: boolean;
  destructive?: boolean;
}

export enum ChapterStatus {
  DRAFT = 'draft',
  IN_PROGRESS = 'in_progress', 
  COMPLETED = 'completed',
  PUBLISHED = 'published'
}
