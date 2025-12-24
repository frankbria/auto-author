'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { HugeiconsIcon } from '@hugeicons/react';
import { MoreVerticalIcon, Edit01Icon, Delete02Icon, Copy01Icon, ViewIcon } from '@hugeicons/core-free-icons';
import { ChapterStatus } from '@/types/chapter-tabs';

interface TabContextMenuProps {
  chapterId?: string;
  onStatusUpdate?: (chapterId: string, status: ChapterStatus) => void;
  onDelete?: (chapterId: string) => void;
  onDuplicate?: (chapterId: string) => void;
  onPreview?: (chapterId: string) => void;
}

export default function TabContextMenu({
  chapterId,
  onStatusUpdate,
  onDelete,
  onDuplicate,
  onPreview
}: TabContextMenuProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!chapterId) {
    return null;
  }

  const handleStatusUpdate = (status: ChapterStatus) => {
    if (onStatusUpdate) {
      onStatusUpdate(chapterId, status);
    }
    setIsOpen(false);
  };

  const handleAction = (action: () => void) => {
    action();
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="sm"
        className="h-6 w-6 p-0"
        onClick={() => setIsOpen(!isOpen)}
      >
        <HugeiconsIcon icon={MoreVerticalIcon} size={12} />
      </Button>
      
      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 top-full z-20 mt-1 w-48 rounded-md border border-border bg-popover text-popover-foreground p-1 shadow-md">
            {onPreview && (
              <button
                className="flex w-full items-center rounded-sm px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground"
                onClick={() => handleAction(() => onPreview(chapterId))}
              >
                <HugeiconsIcon icon={ViewIcon} size={16} className="mr-2" />
                Preview
              </button>
            )}
            
            <button
              className="flex w-full items-center rounded-sm px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground"
              onClick={() => handleAction(() => console.log('Edit chapter', chapterId))}
            >
              <HugeiconsIcon icon={Edit01Icon} size={16} className="mr-2" />
              Edit
            </button>

            {onDuplicate && (
              <button
                className="flex w-full items-center rounded-sm px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground"
                onClick={() => handleAction(() => onDuplicate(chapterId))}
              >
                <HugeiconsIcon icon={Copy01Icon} size={16} className="mr-2" />
                Duplicate
              </button>
            )}

            <div className="my-1 h-px bg-border" />
            
            <button
              className="flex w-full items-center rounded-sm px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground"
              onClick={() => handleStatusUpdate(ChapterStatus.DRAFT)}
            >
              Mark as Draft
            </button>
            <button
              className="flex w-full items-center rounded-sm px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground"
              onClick={() => handleStatusUpdate(ChapterStatus.IN_PROGRESS)}
            >
              Mark as In Progress
            </button>
            <button
              className="flex w-full items-center rounded-sm px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground"
              onClick={() => handleStatusUpdate(ChapterStatus.COMPLETED)}
            >
              Mark as Completed
            </button>
            <button
              className="flex w-full items-center rounded-sm px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground"
              onClick={() => handleStatusUpdate(ChapterStatus.PUBLISHED)}
            >
              Mark as Published
            </button>

            <div className="my-1 h-px bg-border" />
            
            {onDelete && (
              <button
                className="flex w-full items-center rounded-sm px-2 py-1.5 text-sm text-destructive hover:bg-destructive hover:text-destructive-foreground"
                onClick={() => handleAction(() => onDelete(chapterId))}
              >
                <HugeiconsIcon icon={Delete02Icon} size={16} className="mr-2" />
                Delete
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
