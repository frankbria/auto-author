'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { HugeiconsIcon } from '@hugeicons/react';
import { ArrowRight01Icon, ArrowDown01Icon, BookOpen01Icon, Menu01Icon, Cancel01Icon } from '@hugeicons/core-free-icons';
import { TocData, TocChapter } from '@/types/toc';
import { ChapterStatusIndicator } from '@/components/ui/ChapterStatusIndicator';

interface TocSidebarProps {
  tocData: TocData | null;
  activeChapterId?: string | null;
  onChapterSelect?: (chapterId: string) => void;
  className?: string;
  isCollapsible?: boolean;
}

interface TocItemProps {
  chapter: TocChapter;
  level: number;
  isActive: boolean;
  isExpanded: boolean;
  onToggle: () => void;
  onSelect: (chapterId: string) => void;
  activeChapterId?: string | null;
}

function TocItem({ chapter, level, isActive, isExpanded, onToggle, onSelect, activeChapterId }: TocItemProps) {
  const hasSubchapters = chapter.subchapters && chapter.subchapters.length > 0;
  const indentLevel = level * 16; // 16px per level

  return (
    <div className="select-none">
      <div
        className={cn(
          "flex items-center gap-2 py-2 px-3 text-sm cursor-pointer rounded-md transition-colors",
          "hover:bg-muted/50",
          isActive && "bg-indigo-600/10 dark:bg-indigo-600/20 text-indigo-700 dark:text-indigo-400 border-r-2 border-indigo-700 dark:border-indigo-400",
          !isActive && "text-muted-foreground hover:text-foreground"
        )}
        style={{ paddingLeft: `${indentLevel + 12}px` }}
        onClick={() => onSelect(chapter.id)}
      >
        {/* Expand/Collapse Arrow */}
        {hasSubchapters ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggle();
            }}
            className="p-0.5 hover:bg-secondary/50 rounded"
            aria-label={isExpanded ? "Collapse subchapters" : "Expand subchapters"}
          >
            {isExpanded ? (
              <HugeiconsIcon icon={ArrowDown01Icon} size={12} aria-hidden="true" />
            ) : (
              <HugeiconsIcon icon={ArrowRight01Icon} size={12} aria-hidden="true" />
            )}
          </button>
        ) : (
          <div className="w-4" /> // Spacer for alignment
        )}

        {/* Status Indicator */}
        {chapter.status && (
          <ChapterStatusIndicator status={chapter.status} size="sm" />
        )}

        {/* Chapter Title */}
        <span className="flex-1 truncate font-medium">
          {chapter.title}
        </span>

        {/* Word Count Badge */}
        {chapter.word_count > 0 && (
          <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
            {chapter.word_count}w
          </span>
        )}
      </div>

      {/* Subchapters */}
      {hasSubchapters && isExpanded && (
        <div className="ml-2">
          {chapter.subchapters.map((subchapter) => (            <TocItem
              key={subchapter.id}
              chapter={subchapter as TocChapter}
              level={level + 1}
              isActive={activeChapterId === subchapter.id}
              isExpanded={false} // Subchapters don't expand further in this implementation
              onToggle={() => {}} // No-op for subchapters
              onSelect={onSelect}
              activeChapterId={activeChapterId}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function TocSidebar({
  tocData,
  activeChapterId,
  onChapterSelect,
  className,
  isCollapsible = false
}: TocSidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [expandedChapters, setExpandedChapters] = useState<Set<string>>(new Set());

  const toggleChapter = (chapterId: string) => {
    setExpandedChapters(prev => {
      const newSet = new Set(prev);
      if (newSet.has(chapterId)) {
        newSet.delete(chapterId);
      } else {
        newSet.add(chapterId);
      }
      return newSet;
    });
  };

  const handleChapterSelect = (chapterId: string) => {
    onChapterSelect?.(chapterId);
  };

  if (!tocData || !tocData.chapters || tocData.chapters.length === 0) {
    return (
      <div className={cn("w-64 border-r border-border bg-card", className)}>
        <div className="p-4 text-center text-muted-foreground">
          <HugeiconsIcon icon={BookOpen01Icon} size={32} className="mx-auto mb-2 opacity-50" aria-hidden="true" />
          <p className="text-sm">No chapters available</p>
        </div>
      </div>
    );
  }

  if (isCollapsed) {
    return (
      <div className={cn("w-12 border-r border-border bg-card flex flex-col", className)}>
        <button
          onClick={() => setIsCollapsed(false)}
          className="p-3 hover:bg-muted transition-colors"
          aria-label="Expand table of contents"
        >
          <HugeiconsIcon icon={Menu01Icon} size={20} className="text-muted-foreground" aria-hidden="true" />
        </button>
      </div>
    );
  }

  return (
    <div className={cn("w-64 border-r border-border bg-card flex flex-col", className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <HugeiconsIcon icon={BookOpen01Icon} size={16} className="text-indigo-700 dark:text-indigo-400" aria-hidden="true" />
          <h3 className="font-medium text-foreground">Table of Contents</h3>
        </div>
        {isCollapsible && (
          <button
            onClick={() => setIsCollapsed(true)}
            className="p-1 hover:bg-muted rounded transition-colors"
            aria-label="Collapse table of contents"
          >
            <HugeiconsIcon icon={Cancel01Icon} size={16} className="text-muted-foreground" aria-hidden="true" />
          </button>
        )}
      </div>

      {/* TOC Stats */}
      <div className="p-4 border-b border-border">
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="text-center">
            <div className="text-lg font-bold text-foreground">{tocData.total_chapters}</div>
            <div className="text-muted-foreground">Chapters</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-foreground">{tocData.estimated_pages}</div>
            <div className="text-muted-foreground">Pages</div>
          </div>
        </div>
      </div>

      {/* Chapter List */}
      <div className="flex-1 overflow-y-auto p-2">        <div className="space-y-1">
          {tocData.chapters.map((chapter) => (
            <TocItem
              key={chapter.id}
              chapter={chapter}
              level={0}
              isActive={activeChapterId === chapter.id}
              isExpanded={expandedChapters.has(chapter.id)}
              onToggle={() => toggleChapter(chapter.id)}
              onSelect={handleChapterSelect}
              activeChapterId={activeChapterId}
            />
          ))}
        </div>
      </div>

      {/* Footer Actions */}
      <div className="p-4 border-t border-border">
        <div className="flex gap-2">
          <button
            onClick={() => setExpandedChapters(new Set(tocData.chapters.map(ch => ch.id)))}
            className="flex-1 px-2 py-1 text-xs bg-muted hover:bg-secondary text-secondary-foreground rounded transition-colors"
          >
            Expand All
          </button>
          <button
            onClick={() => setExpandedChapters(new Set())}
            className="flex-1 px-2 py-1 text-xs bg-muted hover:bg-secondary text-secondary-foreground rounded transition-colors"
          >
            Collapse All
          </button>
        </div>
      </div>
    </div>
  );
}
