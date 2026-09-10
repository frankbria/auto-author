'use client';

import { forwardRef } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { HugeiconsIcon } from '@hugeicons/react';
import { Cancel01Icon, File01Icon, Clock01Icon, AlertCircleIcon, Loading03Icon } from '@hugeicons/core-free-icons';
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
    // Not `bg-muted`: that is also the inactive tab's own surface, so the dot
    // vanished into it (pre-#618; `bg-white` never applied — twMerge dropped it).
    color: 'bg-muted-foreground',
    icon: File01Icon,
    label: 'Draft'
  },
  [ChapterStatus.IN_PROGRESS]: {
    color: 'bg-blue-500',
    icon: Clock01Icon,
    label: 'In Progress'
  },
  [ChapterStatus.COMPLETED]: {
    // #623: green-500 is 2.09:1 on light `bg-muted`, under the 3:1 non-text
    // floor (WCAG 2.1 1.4.11). green-700 is 4.60:1 there; dark keeps 500.
    color: 'bg-green-700 dark:bg-green-500',
    icon: Clock01Icon,
    label: 'Completed'
  },
  [ChapterStatus.PUBLISHED]: {
    color: 'bg-purple-500',
    icon: Clock01Icon,
    label: 'Published'
  }
};

// #623: the unsaved-changes dot carries the same non-text 1.4.11 obligation as
// the status dots. orange-500 was 2.57:1 on light `bg-muted`; orange-600 is
// 3.26:1 there and improves on every other surface. Named so the contrast guard
// reads the value from here rather than from a duplicated literal.
const UNSAVED_DOT = 'bg-orange-600';

// #629: the loading indicator was a hand-rolled `border-blue-400 ... bg-white`
// ring — 2.33:1 on light `bg-muted`, under the same 3:1 non-text floor — with a
// theme-fixed white core that read as the surface colour in light and as a
// bright dot in dark. It is now the icon spinner used elsewhere in the app (see
// ChapterEditor's save indicator), so there is no fill to be theme-blind about,
// and the stroke keeps the row's blue "working" signal per theme: blue-600 is
// 5.17:1 on light `--background` and 4.74:1 on light `--muted`, blue-400 is
// 7.79 / 5.95 on their dark counterparts. (#629 predicted 3.56/3.26 for the
// light pair; that was Tailwind v4's blue-600 — this repo is still on v3.)
const LOADING_SPINNER = 'text-blue-600 dark:text-blue-400';

// #634: both of these were light-only surfaces — `bg-red-50` with no `dark:`
// counterpart, while the text on top comes from tokens that do flip, so the
// errored tab's label was 1.05:1 (`--foreground`) / 1.15:1 (`--primary`) /
// 2.36:1 (`--muted-foreground`) in dark theme: unreadable, on exactly the tab a
// user needs to read. They now use the `bg-<hue>-50 dark:bg-<hue>-900/20` +
// `border-<hue>-700` idiom the other nine red surfaces in the tree already ship
// (#631). Named so the contrast guard reads the values from here.
const ERROR_TAB = 'border-red-200 bg-red-50 dark:border-red-700 dark:bg-red-900/20';
const UNSAVED_TAB = 'border-orange-200 dark:border-orange-700';

// The alert glyph on the same row, which only renders when `chapter.error` is
// set and so is painted on the surface above. It was `text-red-600`, also
// light-only: 3.01:1 on the dark card over `--muted`, a hair over 1.4.11's 3:1
// floor and pinned by nothing. `text-red-700 dark:text-red-400` is the same
// pair the other red surfaces use — 5.91 light, 5.25-6.70 dark.
const ERROR_ICON = 'text-red-700 dark:text-red-400';

export const ChapterTab = forwardRef<HTMLDivElement, ChapterTabProps>(
  ({ chapter, isActive, isDragging, onSelect, onClose, orientation = 'vertical', ...props }, ref) => {
    const config = statusConfig[chapter.status];
    const statusIcon = config.icon;
    const truncatedTitle = orientation === 'horizontal' && chapter.title.length > 20
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
            data-testid="chapter-tab"
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
              chapter.error && ERROR_TAB,
              chapter.has_unsaved_changes && UNSAVED_TAB
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
            <div className={cn("w-2 h-2 rounded-full flex-shrink-0 border border-border", config.color)} />
            {/* Chapter Title */}
            <span className={cn(
              "text-sm font-semibold truncate flex-1",
              isActive ? "text-primary" : "text-foreground hover:text-primary"
            )}>
              {truncatedTitle}
            </span>

            {/* Indicators */}
            <div className="flex items-center gap-1" data-testid="indicators-container">
              {chapter.has_unsaved_changes && (
                <div className={cn("w-1.5 h-1.5 rounded-full border border-orange-700", UNSAVED_DOT)} />
              )}

              {chapter.is_loading && (
                <HugeiconsIcon icon={Loading03Icon} size={12} className={cn('animate-spin', LOADING_SPINNER)} />
              )}

              {chapter.error && (
                <HugeiconsIcon icon={AlertCircleIcon} size={12} className={ERROR_ICON} />
              )}
            </div>

            {/* Close Button - WCAG 2.1 compliant 44x44px touch target */}
            <Button
              variant="ghost"
              size="sm"
              className="h-11 w-11 p-0 border border-border text-muted-foreground hover:bg-destructive hover:text-destructive-foreground focus:bg-accent focus:text-accent-foreground shadow-sm"
              style={{ opacity: 1 }}
              onClick={(e) => {
                e.stopPropagation();
                onClose();
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  e.stopPropagation();
                  onClose();
                }
              }}
              aria-label="Close chapter"
            >
              <HugeiconsIcon icon={Cancel01Icon} size={16} />
            </Button>
          </div>
        </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-xs bg-popover text-popover-foreground border border-border">
          <div className="space-y-1">
            <p className="font-medium text-foreground">{chapter.title}</p>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <HugeiconsIcon icon={statusIcon} size={12} />
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
