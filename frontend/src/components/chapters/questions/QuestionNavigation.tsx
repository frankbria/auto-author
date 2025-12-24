'use client';

import { Question } from '@/types/chapter-questions';
import { Button } from '@/components/ui/button';
import { HugeiconsIcon } from '@hugeicons/react';
import { ArrowLeft01Icon, ArrowRight01Icon, Tick02Icon, Forward01Icon, Menu01Icon } from '@hugeicons/core-free-icons';
import { useState } from 'react';

interface QuestionNavigationProps {
  currentIndex: number;
  totalQuestions: number;
  onNext: () => void;
  onPrevious: () => void;
  onGoToQuestion: (index: number) => void;
  questions: Question[];
}

/**
 * Component for navigating between questions with next/previous buttons
 * and a dropdown menu for direct navigation to specific questions
 */
export default function QuestionNavigation({
  currentIndex,
  totalQuestions,
  onNext,
  onPrevious,
  onGoToQuestion,
  questions
}: QuestionNavigationProps) {
  const [showQuestionList, setShowQuestionList] = useState(false);
  
  // Determine if we're at the first or last question
  const isFirstQuestion = currentIndex === 0;
  const isLastQuestion = currentIndex === totalQuestions - 1;
  
  // Format question list for dropdown
  const getQuestionTitle = (index: number): string => {
    const question = questions[index];
    
    // Truncate long question text
    const questionText = question.question_text || '';
    const truncatedText = questionText.length > 50 
      ? questionText.substring(0, 50) + '...' 
      : questionText;
    
    // Get question status indicator
    let statusIndicator = '';
    
    if (question.response_status === 'completed') {
      statusIndicator = '✓ ';
    } else if (question.response_status === 'draft') {
      statusIndicator = '⚙️ ';
    }
    
    return `${statusIndicator}${index + 1}. ${truncatedText}`;
  };
  
  return (
    <div className="flex flex-col space-y-2 transition-all" data-slot="question-navigation">
      {/* Main navigation controls */}
      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          size="sm"
          onClick={onPrevious}
          disabled={isFirstQuestion}
          className="flex items-center space-x-1 min-h-[44px] min-w-[44px] transition-all focus-visible:ring-[3px]"
        >
          <HugeiconsIcon icon={ArrowLeft01Icon} size={16} />
          <span>Previous</span>
        </Button>

        <div className="relative">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowQuestionList(!showQuestionList)}
            className="flex items-center space-x-1 min-h-[44px] min-w-[44px] transition-all focus-visible:ring-[3px]"
          >
            <HugeiconsIcon icon={Menu01Icon} size={16} />
            <span>Question {currentIndex + 1} of {totalQuestions}</span>
          </Button>

          {/* Question list dropdown */}
          {showQuestionList && (
            <div className="absolute z-10 mt-1 w-64 max-h-80 overflow-y-auto bg-background border border-border rounded-md shadow-lg transition-all">
              <ul className="py-1">
                {questions.map((_, index) => (
                  <li
                    key={index}
                    className={`px-4 py-2 text-sm cursor-pointer hover:bg-accent transition-all ${
                      index === currentIndex ? 'bg-accent' : ''
                    }`}
                    onClick={() => {
                      onGoToQuestion(index);
                      setShowQuestionList(false);
                    }}
                  >
                    {getQuestionTitle(index)}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={onNext}
          disabled={isLastQuestion}
          className="flex items-center space-x-1 min-h-[44px] min-w-[44px] transition-all focus-visible:ring-[3px]"
        >
          <span>Next</span>
          <HugeiconsIcon icon={ArrowRight01Icon} size={16} />
        </Button>
      </div>

      {/* Secondary actions */}
      <div className="flex justify-center space-x-2">
        <Button
          variant="ghost"
          size="sm"
          className="text-xs min-h-[44px] min-w-[44px] transition-all focus-visible:ring-[3px]"
          onClick={() => {
            // If we're at the last question, go back to the first one
            // Otherwise, go to the next question
            if (isLastQuestion) {
              onGoToQuestion(0);
            } else {
              onNext();
            }
          }}
        >
          {isLastQuestion ? (
            <>
              <HugeiconsIcon icon={Tick02Icon} size={12} className="mr-1" />
              <span>Finish and restart</span>
            </>
          ) : (
            <>
              <HugeiconsIcon icon={Forward01Icon} size={12} className="mr-1" />
              <span>Skip this question</span>
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
