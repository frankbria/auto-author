'use client';

import { useState, useEffect, useRef } from 'react';
import { useToast } from '@/components/ui/use-toast';
import { bookClient } from '@/lib/api/bookClient';
import {
  Question,
  QuestionProgressResponse,
  QuestionType,
  QuestionDifficulty,
} from '@/types/chapter-questions';
import QuestionGenerator from './QuestionGenerator';
import QuestionDisplay from './QuestionDisplay';
import QuestionProgress from './QuestionProgress';
import QuestionNavigation from './QuestionNavigation';
import { DraftGenerationButton } from './DraftGenerationButton';
import { useMediaQuery } from '@/hooks/use-media-query';
import { Button } from '@/components/ui/button';
import { RefreshCw, AlertCircle } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorHandler, classifyError, ErrorType } from '@/lib/errors/errorHandler';

interface QuestionContainerProps {
  bookId: string;
  chapterId: string;
  chapterTitle: string;
  onResponseSaved?: () => void; // Optional callback when a response is saved
  onDraftGenerated?: (draft: string) => void; // Callback when a draft is generated
  onSwitchToEditor?: () => void; // Callback to switch to editor view
}

export default function QuestionContainer({
  bookId,
  chapterId,
  chapterTitle,
  onResponseSaved: parentResponseSaved,
  onDraftGenerated,
  onSwitchToEditor
}: QuestionContainerProps) {
  const { toast } = useToast();

  // State
  const [questions, setQuestions] = useState<Question[]>([]);
  const [cachedQuestions, setCachedQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorType, setErrorType] = useState<ErrorType | null>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [progress, setProgress] = useState<QuestionProgressResponse | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  const isMobile = useMediaQuery('(max-width: 767px)');
  const isTablet = useMediaQuery('(min-width: 768px) and (max-width: 1023px)');
  const isDesktop = useMediaQuery('(min-width: 1024px)');
  const prefersHighContrast = useMediaQuery('(prefers-contrast: high)');
  const prefersReducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)');

  // Ref for screen reader announcements
  const announcementRef = useRef<HTMLDivElement>(null);

  // Error handler with retry logic
  const errorHandlerRef = useRef(new ErrorHandler({
    maxRetries: 3,
    baseDelay: 1000,
    maxDelay: 30000,
  }));

  // Fetch questions with retry logic and stale-while-revalidate
  const fetchQuestions = async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setIsRefreshing(true);
        setError(null);
      } else {
        setLoading(true);
        setError(null);
      }

      // Execute with retry logic
      const response = await errorHandlerRef.current.execute(() =>
        bookClient.getChapterQuestions(bookId, chapterId)
      );

      if (response.questions.length > 0) {
        setQuestions(response.questions);
        setCachedQuestions(response.questions);
        await fetchProgress();
      }

      setError(null);
      setErrorType(null);
    } catch (err) {
      console.error('Error fetching questions:', err);
      const errType = classifyError(err);
      setErrorType(errType);

      // Provide actionable error messages
      let errorMessage = 'Failed to load questions.';
      if (errType === ErrorType.NETWORK) {
        errorMessage = 'Network error. Please check your connection.';
        // Use cached questions if available (stale-while-revalidate)
        if (cachedQuestions.length > 0) {
          setQuestions(cachedQuestions);
          errorMessage += ' Showing cached questions.';
        }
      } else if (errType === ErrorType.AUTH) {
        errorMessage = 'Authentication error. Please sign in again.';
      } else if (errType === ErrorType.SERVER) {
        errorMessage = 'Server error. Our team has been notified.';
      }

      setError(errorMessage);

      toast({
        title: 'Error Loading Questions',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchQuestions();
  }, [bookId, chapterId]);

  // Fetch progress data
  const fetchProgress = async () => {
    try {
      const progressData = await bookClient.getChapterQuestionProgress(bookId, chapterId);
      setProgress(progressData);
    } catch (err) {
      console.error('Error fetching progress:', err);
    }
  };

  // Generate new questions
  const handleGenerateQuestions = async (
    count: number = 10,
    difficulty?: QuestionDifficulty,
    focus?: QuestionType[]
  ) => {
    try {
      setIsGenerating(true);
      setError(null);

      const response = await bookClient.generateChapterQuestions(
        bookId,
        chapterId,
        { count, difficulty, focus }
      );

      setQuestions(response.questions);
      setCurrentQuestionIndex(0);
      await fetchProgress();

      toast({
        title: 'Questions Generated',
        description: `${response.questions.length} questions have been created for this chapter.`,
        variant: 'default',
      });
    } catch (err) {
      console.error('Error generating questions:', err);
      setError('Failed to generate questions. Please try again.');

      toast({
        title: 'Error',
        description: 'Failed to generate questions. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsGenerating(false);
    }
  };

  // Regenerate specific question
  const handleRegenerateQuestion = async (questionId: string) => {
    try {
      setIsGenerating(true);

      // Find the question to regenerate
      const questionToRegenerate = questions.find(q => q.id === questionId);
      if (!questionToRegenerate) {
        throw new Error('Question not found');
      }

      // Call the API to regenerate questions (this will regenerate a single question)
      const response = await bookClient.generateQuestions(bookId);

      if (response.questions && response.questions.length > 0) {
        // Replace the old question with a new one
        const newQuestion = response.questions[0]; // Take the first generated question

        const updatedQuestions = questions.map(q =>
          q.id === questionId ? { ...(newQuestion as any), id: questionId } as Question : q
        );

        setQuestions(updatedQuestions);

        toast({
          title: "Question regenerated",
          description: "A new question has been generated for you.",
          variant: "success"
        });
      }
    } catch (error) {
      console.error('Failed to regenerate question:', error);
      toast({
        title: "Error",
        description: "Failed to regenerate question. Please try again.",
        variant: "destructive"
      });
    } finally {
      setIsGenerating(false);
    }
  };

  // Screen reader announcement helper
  const announceToScreenReader = (message: string) => {
    if (announcementRef.current) {
      announcementRef.current.textContent = message;
    }
  };

  // Navigation handlers
  const handleNextQuestion = () => {
    if (currentQuestionIndex < questions.length - 1) {
      const newIndex = currentQuestionIndex + 1;
      setCurrentQuestionIndex(newIndex);
      announceToScreenReader(`Question ${newIndex + 1} of ${questions.length}`);
    }
  };

  const handlePreviousQuestion = () => {
    if (currentQuestionIndex > 0) {
      const newIndex = currentQuestionIndex - 1;
      setCurrentQuestionIndex(newIndex);
      announceToScreenReader(`Question ${newIndex + 1} of ${questions.length}`);
    }
  };

  const handleGoToQuestion = (index: number) => {
    if (index >= 0 && index < questions.length) {
      setCurrentQuestionIndex(index);
    }
  };

  // Response saved handler
  const handleResponseSaved = async () => {
    await fetchProgress();
    // Call parent callback if provided
    if (parentResponseSaved) {
      parentResponseSaved();
    }
  };

  // If there are no questions, show the generator
  if (questions.length === 0 && !loading) {
    // If there's an error from loading, we should retry loading instead of generating
    const handleRetryOrGenerate = async (
      count?: number,
      difficulty?: QuestionDifficulty,
      focus?: QuestionType[]
    ) => {
      if (error) {
        // If there's a load error, retry fetching existing questions
        await fetchQuestions();
      } else {
        // Otherwise, generate new questions
        await handleGenerateQuestions(count, difficulty, focus);
      }
    };

    return (
      <div className="space-y-4 p-4">
        <h2 className="text-2xl font-bold">Interview Questions</h2>
        <p className="text-muted-foreground">
          Generate interview-style questions to help develop content for &quot;{chapterTitle}&quot;.
          These questions will guide you through key aspects of your chapter.
        </p>

        <QuestionGenerator
          bookId={bookId}
          chapterId={chapterId}
          onGenerate={handleRetryOrGenerate}
          isGenerating={isGenerating || loading}
          error={error}
        />
      </div>
    );
  }

  // Loading skeleton (better UX than blank state)
  if (loading && questions.length === 0) {
    return (
      <div className="space-y-6 p-4">
        {/* Progress skeleton */}
        <div className="space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-2 w-full" />
        </div>

        {/* Question card skeleton */}
        <div className="border rounded-lg p-6 space-y-4">
          <div className="flex items-center justify-between">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-6 w-20" />
          </div>

          <Skeleton className="h-8 w-3/4" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />

          <Skeleton className="h-32 w-full" />

          <div className="flex items-center justify-between">
            <div className="flex gap-2">
              <Skeleton className="h-10 w-24" />
              <Skeleton className="h-10 w-32" />
            </div>
            <div className="flex gap-2">
              <Skeleton className="h-10 w-10" />
              <Skeleton className="h-10 w-10" />
              <Skeleton className="h-10 w-10" />
            </div>
          </div>
        </div>

        {/* Navigation skeleton */}
        <div className="flex items-center justify-between">
          <Skeleton className="h-10 w-24" />
          <Skeleton className="h-10 w-32" />
          <Skeleton className="h-10 w-24" />
        </div>
      </div>
    );
  }

  // Show the current question
  const currentQuestion = questions[currentQuestionIndex];

  // Build container classes
  const containerClasses = [
    'space-y-6 p-4',
    isMobile && 'mobile-layout',
    isTablet && 'tablet-layout',
    isDesktop && 'desktop-layout',
    prefersHighContrast && 'high-contrast',
    prefersReducedMotion && 'reduce-motion'
  ].filter(Boolean).join(' ');

  return (
    <>
      {/* Screen reader live region for announcements */}
      <div
        ref={announcementRef}
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      />

      <main
        className={containerClasses}
        role="main"
        aria-label="Chapter questions interface"
        data-testid="question-container"
        style={{
          ...(prefersReducedMotion && {
            animationDuration: '0s',
            transitionDuration: '0s'
          })
        }}
      >
      {/* Error banner with retry button */}
      {error && (
        <div className="bg-destructive/10 border border-destructive/20 p-4 rounded-md mb-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3 flex-1">
              <AlertCircle className="h-5 w-5 text-destructive mt-0.5" />
              <div className="flex-1">
                <h4 className="text-sm font-semibold text-destructive mb-1">
                  {errorType === ErrorType.NETWORK && 'Network Error'}
                  {errorType === ErrorType.AUTH && 'Authentication Error'}
                  {errorType === ErrorType.SERVER && 'Server Error'}
                  {!errorType && 'Error'}
                </h4>
                <p className="text-sm text-destructive/90">{error}</p>
                {cachedQuestions.length > 0 && errorType === ErrorType.NETWORK && (
                  <p className="text-xs text-muted-foreground mt-2">
                    Showing cached questions. Click retry when connection is restored.
                  </p>
                )}
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchQuestions(true)}
              disabled={isRefreshing}
              className="shrink-0 min-h-[44px] min-w-[44px]"
            >
              {isRefreshing ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Retrying...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Retry
                </>
              )}
            </Button>
          </div>
        </div>
      )}

      {/* Progress bar */}
      {progress && (
        <QuestionProgress
          progress={progress}
          currentIndex={currentQuestionIndex}
          totalQuestions={questions.length}
        />
      )}

      {/* Draft generation button - shows when there are enough completed responses */}
      {progress && questions.length > 0 && (
        <DraftGenerationButton
          bookId={bookId}
          chapterId={chapterId}
          chapterTitle={chapterTitle}
          completedCount={progress.completed}
          totalQuestions={progress.total}
          onDraftGenerated={onDraftGenerated}
          onSwitchToEditor={onSwitchToEditor}
          minimumResponses={3}
        />
      )}

      {/* Question display */}
      {currentQuestion && (
        <QuestionDisplay
          bookId={bookId}
          chapterId={chapterId}
          question={currentQuestion}
          onResponseSaved={handleResponseSaved}
          onRegenerateQuestion={() => handleRegenerateQuestion(currentQuestion.id)}
        />
      )}

      {/* Navigation */}
      <QuestionNavigation
        currentIndex={currentQuestionIndex}
        totalQuestions={questions.length}
        onNext={handleNextQuestion}
        onPrevious={handlePreviousQuestion}
        onGoToQuestion={handleGoToQuestion}
        questions={questions}
      />
    </main>
    </>
  );
}
