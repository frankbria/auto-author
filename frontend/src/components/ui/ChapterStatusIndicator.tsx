'use client';

import { cn } from '@/lib/utils';
import { HugeiconsIcon } from '@hugeicons/react';
import { FileEditIcon, Loading03Icon, CheckmarkCircle01Icon, Book02Icon } from '@hugeicons/core-free-icons';
import { ChapterStatus } from '@/types/chapter-tabs';

interface ChapterStatusIndicatorProps {
  status: ChapterStatus;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  showIcon?: boolean;
  className?: string;
}

const statusConfig = {
  [ChapterStatus.DRAFT]: {
    color: 'bg-gray-500',
    textColor: 'text-gray-600 dark:text-gray-400',
    icon: FileEditIcon,
    label: 'Draft'
  },
  [ChapterStatus.IN_PROGRESS]: {
    color: 'bg-blue-500',
    textColor: 'text-blue-600 dark:text-blue-400',
    icon: Loading03Icon,
    label: 'In Progress'
  },
  [ChapterStatus.COMPLETED]: {
    color: 'bg-green-500',
    textColor: 'text-green-600 dark:text-green-400',
    icon: CheckmarkCircle01Icon,
    label: 'Completed'
  },
  [ChapterStatus.PUBLISHED]: {
    color: 'bg-purple-500',
    textColor: 'text-purple-600 dark:text-purple-400',
    icon: Book02Icon,
    label: 'Published'
  }
};

const sizeConfig = {
  sm: {
    dot: 'w-2 h-2',
    icon: 'w-3 h-3',
    text: 'text-xs'
  },
  md: {
    dot: 'w-3 h-3',
    icon: 'w-4 h-4', 
    text: 'text-sm'
  },
  lg: {
    dot: 'w-4 h-4',
    icon: 'w-5 h-5',
    text: 'text-base'
  }
};

export function ChapterStatusIndicator({
  status,
  size = 'sm',
  showLabel = false,
  showIcon = false,
  className
}: ChapterStatusIndicatorProps) {
  const config = statusConfig[status];
  const sizes = sizeConfig[size];

  if (showIcon && showLabel) {
    return (
      <div data-slot="status-indicator" className={cn("flex items-center gap-2 transition-all", className)}>
        <HugeiconsIcon icon={config.icon} size={parseInt(sizes.icon.split('-')[1])} className={config.textColor} />
        <span className={cn(sizes.text, config.textColor)}>{config.label}</span>
      </div>
    );
  }

  if (showIcon) {
    return (
      <HugeiconsIcon
        data-slot="status-icon"
        icon={config.icon}
        size={parseInt(sizes.icon.split('-')[1])}
        className={cn(config.textColor, 'transition-all', className)}
        role="status"
        aria-label={config.label}
      />
    );
  }

  if (showLabel) {
    return (
      <span data-slot="status-label" className={cn(sizes.text, config.textColor, 'transition-all', className)}>
        {config.label}
      </span>
    );
  }

  // Default: just show colored dot
  return (
    <div
      data-slot="status-dot"
      className={cn(
        "rounded-full flex-shrink-0 transition-all",
        sizes.dot,
        config.color,
        className
      )}
      title={config.label}
      role="status"
      aria-label={config.label}
    />
  );
}
