'use client';

import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { MoreHorizontal } from 'lucide-react';
import { ChapterTabMetadata } from '@/types/chapter-tabs';

interface TabOverflowMenuProps {
  chapters: ChapterTabMetadata[];
  activeChapterId: string | null;
  onTabSelect: (chapterId: string) => void;
  visible: boolean;
  onVisibilityChange: (visible: boolean) => void;
}

export function TabOverflowMenu({
  chapters,
  activeChapterId,
  onTabSelect,
  visible,
  onVisibilityChange
}: TabOverflowMenuProps) {
  if (!visible || chapters.length === 0) {
    return null;
  }

  return (
    <DropdownMenu open={visible} onOpenChange={onVisibilityChange}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="px-2">
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        {chapters.map((chapter) => (
          <DropdownMenuItem
            key={chapter.id}
            onClick={() => onTabSelect(chapter.id)}
            className={activeChapterId === chapter.id ? 'bg-accent' : ''}
          >
            <span className="truncate">{chapter.title}</span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
