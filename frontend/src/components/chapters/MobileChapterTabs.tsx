
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Menu } from 'lucide-react';
import { ChapterTabMetadata } from '@/types/chapter-tabs';
import { cn } from '@/lib/utils';

interface MobileChapterTabsProps {
  chapters: ChapterTabMetadata[];
  activeChapterId: string | null;
  onChapterSelect: (chapterId: string) => void;
}

export function MobileChapterTabs({ 
  chapters, 
  activeChapterId, 
  onChapterSelect 
}: MobileChapterTabsProps) {
  const [isOpen, setIsOpen] = useState(false);
  
  const activeChapter = chapters.find(ch => ch.id === activeChapterId);

  return (
    <div className="md:hidden border-b bg-background p-2">
      {/* Chapter Selector */}
      <Select value={activeChapterId || ''} onValueChange={onChapterSelect}>
        <SelectTrigger className="w-full">
          <SelectValue placeholder="Select a chapter">
            {activeChapter && (
              <div className="flex items-center gap-2">
                <div className={cn("w-2 h-2 rounded-full", getStatusColor(activeChapter.status))} />
                <span className="truncate">{activeChapter.title}</span>
              </div>
            )}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {chapters.map((chapter) => (
            <SelectItem key={chapter.id} value={chapter.id}>
              <div className="flex items-center gap-2 w-full">
                <div className={cn("w-2 h-2 rounded-full", getStatusColor(chapter.status))} />
                <span className="truncate">{chapter.title}</span>
                <span className="text-xs text-muted-foreground ml-auto">
                  {chapter.word_count}w
                </span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Chapter Navigation Sheet */}
      <Sheet open={isOpen} onOpenChange={setIsOpen}>
        <SheetTrigger asChild>
          <Button variant="outline" size="sm" className="mt-2 w-full">
            <Menu className="w-4 h-4 mr-2" />
            Chapter Options
          </Button>
        </SheetTrigger>
        <SheetContent side="bottom" className="h-[50vh]">
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Chapters</h3>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {chapters.map((chapter) => (
                <div
                  key={chapter.id}
                  className={cn(
                    "p-3 rounded-lg border cursor-pointer transition-colors",
                    chapter.id === activeChapterId 
                      ? "bg-primary/10 border-primary" 
                      : "hover:bg-muted"
                  )}
                  onClick={() => {
                    onChapterSelect(chapter.id);
                    setIsOpen(false);
                  }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className={cn("w-2 h-2 rounded-full", getStatusColor(chapter.status))} />
                      <span className="font-medium">{chapter.title}</span>
                    </div>
                    <span className="text-sm text-muted-foreground">
                      {chapter.word_count} words
                    </span>
                  </div>
                  {chapter.last_modified && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Modified {new Date(chapter.last_modified).toLocaleDateString()}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'draft': return 'bg-muted';
    case 'in_progress': return 'bg-blue-500';
    case 'completed': return 'bg-green-500';
    case 'published': return 'bg-purple-500';
    default: return 'bg-muted';
  }
}