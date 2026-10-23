'use client';

import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { HugeiconsIcon } from '@hugeicons/react';
import { Menu01Icon } from '@hugeicons/core-free-icons';
import { ChapterTabMetadata } from '@/types/chapter-tabs';

interface AllChaptersMenuProps {
  chapters: ChapterTabMetadata[];
  tabOrder: string[];
  activeChapterId: string | null;
  onSelect: (chapterId: string) => void;
}

/** Every chapter, so one whose tab was closed can be reopened (#1043). */
export function AllChaptersMenu({ chapters, tabOrder, activeChapterId, onSelect }: AllChaptersMenuProps) {
  if (chapters.length === 0) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="px-2" aria-label="All chapters">
          <HugeiconsIcon icon={Menu01Icon} size={16} />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        {chapters.map(chapter => (
          <DropdownMenuItem
            key={chapter.id}
            onSelect={() => onSelect(chapter.id)}
            className={activeChapterId === chapter.id ? 'bg-accent' : ''}
          >
            <span className="truncate">{chapter.title}</span>
            {!tabOrder.includes(chapter.id) && <span className="ml-auto text-xs text-muted-foreground">closed</span>}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
