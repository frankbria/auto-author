'use client';

import { forwardRef } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { X, FileText, Clock, AlertCircle } from 'lucide-react';
import { ChapterTabMetadata, ChapterStatus } from '@/types/chapter-tabs';

interface ChapterTabProps {
  chapter: ChapterTabMetadata;
  isActive: boolean;
  isDragging?: boolean;
  onSelect: () => void;
  onClose: () => void;
  orientation?: 'horizontal' | 'vertical';
}

const statusConfig = {
  [ChapterStatus.DRAFT]: { 
    color: 'bg-muted', 
    icon: FileText, 
    label: 'Draft' 
  },
  [ChapterStatus.IN_PROGRESS]: { 
    color: 'bg-blue-500', 
    icon: Clock, 
    label: 'In Progress' 
  },
  [ChapterStatus.COMPLETED]: { 
    color: 'bg-green-500',
    icon: Clock, 
    label: 'Completed' 
  },
  [ChapterStatus.PUBLISHED]: { 
    color: 'bg-purple-500', 
    icon: Clock, 
    label: 'Published' 
  }
};

export const ChapterTab = forwardRef<HTMLDivElement, ChapterTabProps>(
  ({ chapter, isActive, isDragging, onSelect, onClose, orientation = 'vertical', ...props }, ref) => {
    const config = statusConfig[chapter.status];
    const StatusIcon = config.icon;    const truncatedTitle = orientation === 'horizontal' && chapter.title.length > 20 
      ? `${chapter.title.substring(0, 20)}...` 
      : chapter.title;

    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            ref={ref}
            {...props}
            role="button"
            tabIndex={0}
            aria-label={`Open chapter ${chapter.title}`}
            aria-selected={isActive}
            className={cn(
              "group relative flex items-center gap-2 cursor-pointer transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
              orientation === 'horizontal'
                ? "px-3 py-2 border-r min-w-0 max-w-[200px]"
                : "px-3 py-3 w-full min-h-[48px]",
              isActive
                ? orientation === 'horizontal'
                  ? "bg-background border-b-2 border-b-primary text-foreground"
                  : "bg-background border-r-2 border-r-primary text-foreground"
                : "bg-muted hover:bg-background text-muted-foreground hover:text-foreground",
              isDragging && "opacity-50",
              chapter.error && "border-red-200 bg-red-50",
              chapter.has_unsaved_changes && "border-orange-200"
            )}
            onClick={onSelect}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onSelect();
              }
            }}
          >
            {/* Status Indicator */}
            <div className={cn("w-2 h-2 rounded-full flex-shrink-0 border border-zinc-400 bg-white", config.color)} />            
            {/* Chapter Title */}
            <span className={cn(
              "text-sm font-semibold truncate flex-1",
              isActive ? "text-primary" : "text-zinc-700 hover:text-primary"
            )}>
              {truncatedTitle}
            </span>

            {/* Indicators */}
            <div className="flex items-center gap-1" data-testid="indicators-container">
              {chapter.has_unsaved_changes && (
                <div className="w-1.5 h-1.5 bg-orange-500 rounded-full border border-orange-700" />
              )}
              
              {chapter.is_loading && (
                <div className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin bg-white" />
              )}

              {chapter.error && (
                <AlertCircle className="w-3 h-3 text-red-600" />
              )}
            </div>

            {/* Close Button - WCAG 2.1 compliant 44x44px touch target */}
            <Button
              variant="ghost"
              size="sm"
              className="h-11 w-11 p-0 border border-zinc-300 bg-zinc-100 text-zinc-700 hover:bg-destructive hover:text-destructive-foreground focus:bg-zinc-200 focus:text-zinc-900 shadow-sm"
              style={{ opacity: 1 }}
              onClick={(e) => {
                e.stopPropagation();
                onClose();
              }}
              aria-label="Close chapter"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-xs bg-popover text-popover-foreground border border-border">
          <div className="space-y-1">
            <p className="font-medium text-foreground">{chapter.title}</p>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <StatusIcon className="w-3 h-3" />
              <span>{config.label}</span>
              <span>•</span>
              <span>{chapter.word_count} words</span>
              <span>•</span>
              <span>{chapter.estimated_reading_time}min read</span>
            </div>
            {chapter.last_modified && (
              <p className="text-xs text-muted-foreground">
                Modified {new Date(chapter.last_modified).toLocaleString()}
              </p>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    );
  }
);

ChapterTab.displayName = 'ChapterTab';
