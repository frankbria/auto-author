'use client';

import { cn } from '@/lib/utils';
import { FileText, Clock, CheckCircle, BookOpen } from 'lucide-react';
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
    textColor: 'text-gray-600',
    icon: FileText, 
    label: 'Draft' 
  },
  [ChapterStatus.IN_PROGRESS]: { 
    color: 'bg-blue-500', 
    textColor: 'text-blue-600',
    icon: Clock, 
    label: 'In Progress' 
  },
  [ChapterStatus.COMPLETED]: { 
    color: 'bg-green-500', 
    textColor: 'text-green-600',
    icon: CheckCircle, 
    label: 'Completed' 
  },
  [ChapterStatus.PUBLISHED]: { 
    color: 'bg-purple-500', 
    textColor: 'text-purple-600',
    icon: BookOpen, 
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
  const StatusIcon = config.icon;

  if (showIcon && showLabel) {
    return (
      <div className={cn("flex items-center gap-2", className)}>
        <StatusIcon className={cn(sizes.icon, config.textColor)} />
        <span className={cn(sizes.text, config.textColor)}>{config.label}</span>
      </div>
    );
  }

  if (showIcon) {
    return (
      <StatusIcon className={cn(sizes.icon, config.textColor, className)} />
    );
  }

  if (showLabel) {
    return (
      <span className={cn(sizes.text, config.textColor, className)}>
        {config.label}
      </span>
    );
  }

  // Default: just show colored dot
  return (
    <div 
      className={cn(
        "rounded-full flex-shrink-0",
        sizes.dot,
        config.color,
        className
      )}
      title={config.label}
    />
  );
}
