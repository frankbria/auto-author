'use client';

import { QuestionProgressResponse } from '@/types/chapter-questions';
import { HugeiconsIcon } from '@hugeicons/react';
import { CheckmarkCircle01Icon, CircleIcon, Loading03Icon } from '@hugeicons/core-free-icons';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

// Stub component for Progress since the real one isn't available
const Progress = ({ value, className }: { value: number, className?: string }) => (
  <div className={`w-full bg-gray-200 rounded-full ${className || ''}`}>
    <div
      className="bg-primary rounded-full h-full transition-all duration-300 ease-in-out"
      style={{ width: `${value}%` }}
    ></div>
  </div>
);

interface QuestionProgressProps {
  progress: QuestionProgressResponse;
  currentIndex: number;
  totalQuestions: number;
}

/**
 * Component to display question completion progress with visual indicators
 */
export default function QuestionProgress({
  progress,
  currentIndex,
  totalQuestions
}: QuestionProgressProps) {
  // Calculate progress percentage for the progress bar (progress is 0.0-1.0, convert to 0-100)
  const progressPercentage = (progress.progress || 0) * 100;

  // Calculate current position
  const currentPosition = currentIndex + 1;

  // Determine status label
  let statusLabel = '';
  let statusColor = '';

  if (progress.status === 'completed') {
    statusLabel = 'All questions completed';
    statusColor = 'text-green-600';
  } else if (progress.status === 'in-progress') {
    statusLabel = `${progress.completed} of ${progress.total} questions answered`;
    statusColor = 'text-amber-600';
  } else {
    statusLabel = 'Not started';
    statusColor = 'text-gray-500';
  }
  
  // Stub components if real UI components aren't available
  const StubTooltip = ({ children, content }: { children: React.ReactNode, content: React.ReactNode }) => (
    <div className="relative group">
      {children}
      <div className="absolute z-10 invisible group-hover:visible bg-black/80 text-white text-xs rounded p-2 bottom-full mb-1 left-1/2 transform -translate-x-1/2 w-max max-w-xs">
        {content}
      </div>
    </div>
  );
  
  return (
    <section aria-label="Question progress" className="space-y-2 transition-all" role="region" data-slot="question-progress">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium transition-all">Progress</h4>

        <div className="flex items-center space-x-2">
          <span className={`text-sm ${statusColor} font-medium transition-all`}>
            {statusLabel}
          </span>

          {progress.status === 'completed' ? (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger aria-label="All questions completed">
                  <HugeiconsIcon icon={CheckmarkCircle01Icon} size={16} className="text-green-600 dark:text-green-400 transition-all" />
                </TooltipTrigger>
                <TooltipContent>
                  <p>All questions completed</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : progress.status === 'in-progress' ? (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger aria-label="Some questions still need answers">
                  <HugeiconsIcon icon={Loading03Icon} size={16} className="text-amber-600 dark:text-amber-400 transition-all" />
                </TooltipTrigger>
                <TooltipContent>
                  <p>Some questions still need answers</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger aria-label="No questions answered yet">
                  <HugeiconsIcon icon={CircleIcon} size={16} className="text-gray-400 transition-all" />
                </TooltipTrigger>
                <TooltipContent>
                  <p>No questions answered yet</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
      </div>
      
      {/* Progress bar */}
      <div
        role="progressbar"
        aria-label="Question progress"
        aria-valuenow={isNaN(progressPercentage) ? 0 : Math.round(progressPercentage)}
        aria-valuemin={0}
        aria-valuemax={100}
        className="w-full transition-all"
        data-testid="question-progressbar"
      >
        <Progress value={progressPercentage} className="h-2 transition-all" />
      </div>

      {/* Question position indicator */}
      <div className="flex justify-between text-xs text-muted-foreground transition-all">
        <span>Question {currentPosition} of {totalQuestions}</span>
        <span>{isNaN(progressPercentage) ? 0 : Math.round(progressPercentage)}% complete</span>
      </div>
      
      {/* Question dots - visual representation of each question's status */}
      <div className="flex items-center justify-center space-x-1 mt-2 transition-all">
        {Array.from({ length: totalQuestions }).map((_, index) => {
          // For each question, show its status
          const isCompleted = index < progress.completed;
          const isInProgress = index === progress.completed && progress.in_progress > 0;
          const isCurrent = index === currentIndex;

          let dotClasses = "w-2 h-2 rounded-full transition-all ";

          if (isCompleted) {
            dotClasses += "bg-green-600 dark:bg-green-500";
          } else if (isInProgress) {
            dotClasses += "bg-amber-600 dark:bg-amber-500";
          } else if (isCurrent) {
            dotClasses += "bg-blue-600 dark:bg-blue-500";
          } else {
            dotClasses += "bg-gray-300 dark:bg-gray-700";
          }

          // Add subtle pulsing effect to current question with enhanced focus
          if (isCurrent) {
            dotClasses += " ring-[3px] ring-blue-300 dark:ring-blue-700 ring-opacity-50";
          }

          return (
            <StubTooltip
              key={index}
              content={
                isCompleted ? "Completed" :
                isInProgress ? "In progress" :
                isCurrent ? "Current question" :
                "Not started"
              }
            >
              <div className={dotClasses} data-slot="progress-dot"></div>
            </StubTooltip>
          );
        })}
      </div>
    </section>
  );
}
