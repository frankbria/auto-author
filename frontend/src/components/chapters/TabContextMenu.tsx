'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { MoreVertical, Edit, Trash2, Copy, Eye } from 'lucide-react';
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
        <MoreVertical className="h-3 w-3" />
      </Button>
      
      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 top-full z-20 mt-1 w-48 rounded-md border bg-popover p-1 shadow-md">
            {onPreview && (
              <button
                className="flex w-full items-center rounded-sm px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground"
                onClick={() => handleAction(() => onPreview(chapterId))}
              >
                <Eye className="w-4 h-4 mr-2" />
                Preview
              </button>
            )}
            
            <button
              className="flex w-full items-center rounded-sm px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground"
              onClick={() => handleAction(() => console.log('Edit chapter', chapterId))}
            >
              <Edit className="w-4 h-4 mr-2" />
              Edit
            </button>

            {onDuplicate && (
              <button
                className="flex w-full items-center rounded-sm px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground"
                onClick={() => handleAction(() => onDuplicate(chapterId))}
              >
                <Copy className="w-4 h-4 mr-2" />
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
                <Trash2 className="w-4 h-4 mr-2" />
                Delete
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
