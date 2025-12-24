'use client';

import { Question, QuestionType, QuestionDifficulty, ResponseStatus } from '@/types/chapter-questions';
import { Card, CardContent, CardDescription, CardFooter, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ThumbsUp, ThumbsDown, RefreshCw, HelpCircle, BookOpen, Map as MapIcon, MessageSquare, Search, Star, StarHalf, StarOff, WifiOff, Check, AlertCircle, Loader2 } from 'lucide-react';
import { useState, useEffect, useCallback, useRef } from 'react';
import { bookClient } from '@/lib/api/bookClient';
import { VoiceTextInput } from '@/components/chapters/VoiceTextInput';
import { useOnlineStatus } from '@/hooks/useOnlineStatus';
import { retryQueue } from '@/lib/utils/retryQueue';
import { ErrorHandler, classifyError, ErrorType } from '@/lib/errors/errorHandler';
import { useToast } from '@/components/ui/use-toast';

interface QuestionDisplayProps {
  bookId: string;
  chapterId: string;
  question: Question;
  onResponseSaved: () => void;
  onRegenerateQuestion: (questionId: string) => void;
}

/**
 * Component for displaying a single question with response textarea
 * and actions for saving, rating, etc.
 */
export default function QuestionDisplay({
  bookId,
  chapterId,
  question,
  onResponseSaved,
  onRegenerateQuestion
}: QuestionDisplayProps) {
  // Toast for notifications
  const { toast } = useToast();

  // State for response text
  const [responseText, setResponseText] = useState('');
  // State for auto-saving
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error' | 'queued'>('idle');
  const [saveError, setSaveError] = useState('');
  // State for response completion
  const [isCompleted, setIsCompleted] = useState(false);
  // State for word count
  const [wordCount, setWordCount] = useState(0);
  // State for rating
  const [rating, setRating] = useState(0);
  // State for retry attempts
  const [retryCount, setRetryCount] = useState(0);
  // State to track last attempted action for proper retry behavior
  const [lastAction, setLastAction] = useState<'draft' | 'complete' | null>(null);

  // Online status
  const { isOnline, wasOffline } = useOnlineStatus();

  // Error handler with retry logic
  const errorHandlerRef = useRef(new ErrorHandler({
    maxRetries: 3,
    baseDelay: 1000,
    maxDelay: 30000,
  }));

  // Load existing response if available
  useEffect(() => {
    const fetchResponse = async () => {
      try {
        const result = await bookClient.getQuestionResponse(bookId, chapterId, question.id);
        if (result && result.response) {
          setResponseText(result.response.response_text || '');
          setWordCount((result.response.response_text || '').split(/\s+/).filter(Boolean).length);
          setIsCompleted(result.response.status === ResponseStatus.COMPLETED);
        }
      } catch (error) {
        console.error('Error fetching response:', error);
      }
    };

    if (question.id) {
      fetchResponse();
    }

    // Reset states when question changes
    return () => {
      setResponseText('');
      setWordCount(0);
      setIsCompleted(false);
      setSaveStatus('idle');
      setSaveError('');
      setRating(0);
    };
  }, [bookId, chapterId, question.id]);

  // Update word count when response text changes
  useEffect(() => {
    setWordCount(responseText.split(/\s+/).filter(Boolean).length);
  }, [responseText]);

  // Get question type icon
  const getQuestionTypeIcon = (type: QuestionType) => {
    switch (type) {
      case QuestionType.CHARACTER:
        return <MessageSquare className="h-5 w-5 text-purple-500" />;
      case QuestionType.PLOT:
        return <BookOpen className="h-5 w-5 text-blue-500" />;
      case QuestionType.SETTING:
        return <MapIcon className="h-5 w-5 text-green-500" />;
      case QuestionType.THEME:
        return <Star className="h-5 w-5 text-amber-500" />;
      case QuestionType.RESEARCH:
        return <Search className="h-5 w-5 text-red-500" />;
      default:
        return <HelpCircle className="h-5 w-5 text-gray-500" />;
    }
  };

  // Get difficulty icon and text
  const getDifficultyInfo = (difficulty: QuestionDifficulty) => {
    switch (difficulty) {
      case QuestionDifficulty.EASY:
        return {
          icon: <StarOff className="h-5 w-5 text-green-500" />,
          text: 'Easy'
        };
      case QuestionDifficulty.MEDIUM:
        return {
          icon: <StarHalf className="h-5 w-5 text-amber-500" />,
          text: 'Medium'
        };
      case QuestionDifficulty.HARD:
        return {
          icon: <Star className="h-5 w-5 text-red-500" />,
          text: 'Hard'
        };
      default:
        return {
          icon: <StarHalf className="h-5 w-5 text-gray-500" />,
          text: 'Medium'
        };
    }
  };

  // Get suggested response length
  const getSuggestedLength = () => {
    return question.metadata?.suggested_response_length || 'No specific length requirement';
  };

  // Save operation with retry logic and verification
  const saveOperation = useCallback(async (status: ResponseStatus) => {
    const operation = async () => {
      // Save the response
      const saveResult = await bookClient.saveQuestionResponse(
        bookId,
        chapterId,
        question.id,
        {
          response_text: responseText,
          status
        }
      );

      // VERIFICATION: Fetch the saved response to confirm persistence
      try {
        const verificationResult = await bookClient.getQuestionResponse(
          bookId,
          chapterId,
          question.id
        );

        if (!verificationResult.has_response || !verificationResult.response) {
          console.error('Verification failed: Response not found in database after save');
          // Throw error to trigger centralized error handler (catch block below)
          // which will display a single "Verification Warning" toast
          throw new Error('Failed to verify response persistence');
        }

        // Compare saved data with what was sent
        const savedResponse = verificationResult.response;
        const sentText = responseText;
        const savedText = savedResponse.response_text;

        if (savedText !== sentText) {
          console.warn(
            'Verification warning: Saved text differs from sent text',
            { sent: sentText.substring(0, 100), saved: savedText.substring(0, 100) }
          );
          toast({
            title: 'Warning: Data Mismatch',
            description: 'The saved response may differ from what you submitted. Please review.',
            variant: 'destructive',
          });
        }

        // Log successful verification
        console.log(
          `Verification successful: Response confirmed in database (question_id=${question.id}, status=${savedResponse.status})`
        );
      } catch (verifyError) {
        console.error('Verification query failed:', verifyError);
        // Show warning but don't fail the save operation
        toast({
          title: 'Verification Warning',
          description: 'Response saved but verification failed. Please refresh to confirm.',
          variant: 'destructive',
        });
      }

      return saveResult;
    };

    return errorHandlerRef.current.execute(operation);
  }, [bookId, chapterId, question.id, responseText, toast]);

  // Handle save as draft with enhanced error handling
  const handleSaveDraft = useCallback(async () => {
    if (!responseText.trim()) return;

    setLastAction('draft'); // Track that we're attempting a draft save
    setIsSaving(true);
    setSaveStatus('saving');
    setSaveError('');

    try {
      // Check if offline
      if (!isOnline) {
        setSaveStatus('queued');
        setSaveError('You are offline. Save will be attempted when connection is restored.');

        // Queue the save operation
        const queueId = `save-draft-${question.id}-${Date.now()}`;
        retryQueue.add(
          queueId,
          () => saveOperation(ResponseStatus.DRAFT),
          {
            onSuccess: () => {
              setSaveStatus('saved');
              setSaveError('');
              setLastAction(null); // Clear last action on queued success
              onResponseSaved();
              // Auto-clear saved status after 3 seconds
              setTimeout(() => setSaveStatus('idle'), 3000);
            },
            onError: (error) => {
              setSaveStatus('error');
              const errorType = classifyError(error);
              const errorMessage = errorType === ErrorType.NETWORK
                ? 'Network error. Save will retry automatically.'
                : 'Failed to save draft after multiple attempts.';
              setSaveError(errorMessage);
            }
          }
        );

        setIsSaving(false);
        return;
      }

      // Execute with retry logic
      await saveOperation(ResponseStatus.DRAFT);

      setSaveStatus('saved');
      setSaveError('');
      setRetryCount(0);
      setLastAction(null); // Clear last action on success

      // Notify parent component that response was saved
      onResponseSaved();

      // Auto-clear saved status after 3 seconds
      setTimeout(() => setSaveStatus('idle'), 3000);
    } catch (error) {
      console.error('Error saving draft:', error);
      const errorType = classifyError(error);

      setRetryCount(prev => prev + 1);
      setSaveStatus('error');

      // Provide actionable error messages
      let errorMessage = 'Failed to save draft.';
      if (errorType === ErrorType.NETWORK) {
        errorMessage = 'Network error. Please check your connection and try again.';
      } else if (errorType === ErrorType.AUTH) {
        errorMessage = 'Authentication error. Please sign in again.';
      } else if (errorType === ErrorType.SERVER) {
        errorMessage = 'Server error. Our team has been notified. Please try again.';
      } else if (errorType === ErrorType.VALIDATION) {
        errorMessage = 'Invalid response format. Please check your input.';
      }

      setSaveError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  }, [responseText, bookId, chapterId, question.id, onResponseSaved, isOnline, saveOperation]);

  // Auto-save functionality
  useEffect(() => {
    let autoSaveTimer: NodeJS.Timeout;

    if (responseText.trim() && !isSaving) {
      autoSaveTimer = setTimeout(() => {
        handleSaveDraft();
      }, 3000); // Auto-save after 3 seconds of inactivity
    }

    return () => {
      if (autoSaveTimer) {
        clearTimeout(autoSaveTimer);
      }
    };
  }, [responseText, isSaving, handleSaveDraft]);

  // Handle mark as completed with enhanced error handling
  const handleMarkCompleted = async () => {
    if (!responseText.trim()) {
      setSaveError('Please provide a response before marking as completed');
      return;
    }

    setLastAction('complete'); // Track that we're attempting to complete
    setIsSaving(true);
    setSaveStatus('saving');
    setSaveError('');

    try {
      // Check if offline
      if (!isOnline) {
        setSaveStatus('queued');
        setSaveError('You are offline. Completion will be saved when connection is restored.');

        // Queue the save operation
        const queueId = `complete-${question.id}-${Date.now()}`;
        retryQueue.add(
          queueId,
          () => saveOperation(ResponseStatus.COMPLETED),
          {
            onSuccess: () => {
              setIsCompleted(true);
              setSaveStatus('saved');
              setSaveError('');
              setLastAction(null); // Clear last action on queued success
              onResponseSaved();
              setTimeout(() => setSaveStatus('idle'), 3000);
            },
            onError: (error) => {
              setSaveStatus('error');
              const errorType = classifyError(error);
              const errorMessage = errorType === ErrorType.NETWORK
                ? 'Network error. Completion will retry automatically.'
                : 'Failed to complete response after multiple attempts.';
              setSaveError(errorMessage);
            }
          }
        );

        setIsSaving(false);
        return;
      }

      // Execute with retry logic
      await saveOperation(ResponseStatus.COMPLETED);

      setIsCompleted(true);
      setSaveStatus('saved');
      setSaveError('');
      setRetryCount(0);
      setLastAction(null); // Clear last action on success

      // Notify parent component that response was saved
      onResponseSaved();

      // Auto-clear saved status after 3 seconds
      setTimeout(() => setSaveStatus('idle'), 3000);
    } catch (error) {
      console.error('Error marking as completed:', error);
      const errorType = classifyError(error);

      setRetryCount(prev => prev + 1);
      setSaveStatus('error');

      // Provide actionable error messages
      let errorMessage = 'Failed to complete response.';
      if (errorType === ErrorType.NETWORK) {
        errorMessage = 'Network error. Please check your connection and try again.';
      } else if (errorType === ErrorType.AUTH) {
        errorMessage = 'Authentication error. Please sign in again.';
      } else if (errorType === ErrorType.SERVER) {
        errorMessage = 'Server error. Our team has been notified. Please try again.';
      }

      setSaveError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  // Handle rating the question
  const handleRateQuestion = async (rating: number) => {
    setRating(rating);

    try {
      await bookClient.rateQuestion(
        bookId,
        chapterId,
        question.id,
        {
          rating
        }
      );
    } catch (error) {
      console.error('Error rating question:', error);
    }
  };

  // Handle regenerating the question
  const handleRegenerateQuestion = () => {
    if (onRegenerateQuestion) {
      onRegenerateQuestion(question.id);
    }
  };

  const difficultyInfo = getDifficultyInfo(question.difficulty);

  return (
    <Card className="w-full" data-testid="question-scroll-container" style={{ overflowY: 'auto', scrollBehavior: 'smooth', WebkitOverflowScrolling: 'touch' } as React.CSSProperties}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {getQuestionTypeIcon(question.question_type)}
            <h2 className="text-xl" id="question-heading">{question.question_type} Question</h2>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-sm text-muted-foreground flex items-center">
              {difficultyInfo.icon}
              <span className="ml-1">{difficultyInfo.text}</span>
            </span>
          </div>
        </div>

        <CardDescription>
          {/* Question text */}
          <p className="text-lg font-medium mt-4 mb-2 break-words" id="question-text" style={{ wordWrap: 'break-word' }}>{question.question_text}</p>
          {/* Help text and examples if available */}
          {question.metadata?.help_text && (
            <div className="mt-2 text-sm text-muted-foreground" id="question-help-text">
              <p>{question.metadata.help_text}</p>
            </div>
          )}

          {question.metadata?.examples && question.metadata.examples.length > 0 && (
            <div className="mt-2 text-sm bg-muted/50 p-2 rounded-md">
              <p className="font-medium mb-1">Examples:</p>
              <ul className="list-disc list-inside space-y-1">
                {question.metadata.examples.map((example, i) => (
                  <li key={i}>{example}</li>
                ))}
              </ul>
            </div>
          )}
        </CardDescription>
      </CardHeader>

      <CardContent>
        {/* Response textarea */}
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <label htmlFor="response" className="text-sm font-medium" id="response-label">
              Your Response
            </label>

            <div className="flex items-center space-x-4">
              <span className="text-xs text-muted-foreground">
                Suggested length: {getSuggestedLength()}
              </span>

              <span className="text-xs text-muted-foreground">
                {wordCount} words
              </span>
            </div>
          </div>

          <VoiceTextInput
            id="response"
            value={responseText}
            onChange={setResponseText}
            placeholder="Type your response here or use voice input..."
            className="min-h-[200px] min-w-[44px]"
            disabled={isSaving || isCompleted}
            aria-label="Your response to the question"
          />

          {/* Save status and error with visual indicators */}
          <div className="flex items-center justify-between">
            {/* Save status indicator */}
            {saveStatus !== 'idle' && (
              <div className="flex items-center gap-2 text-xs">
                {saveStatus === 'saving' && (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                    <span className="text-blue-600">Saving...</span>
                  </>
                )}
                {saveStatus === 'saved' && (
                  <>
                    <Check className="h-4 w-4 text-green-600" />
                    <span className="text-green-600">Saved successfully</span>
                  </>
                )}
                {saveStatus === 'error' && (
                  <>
                    <AlertCircle className="h-4 w-4 text-red-600" />
                    <span className="text-red-600">Save failed</span>
                  </>
                )}
                {saveStatus === 'queued' && (
                  <>
                    <WifiOff className="h-4 w-4 text-amber-600" />
                    <span className="text-amber-600">Queued for retry</span>
                  </>
                )}
              </div>
            )}

            {/* Offline indicator */}
            {!isOnline && (
              <div className="flex items-center gap-2 text-xs text-amber-600">
                <WifiOff className="h-4 w-4" />
                <span>Offline mode</span>
              </div>
            )}

            {/* Reconnected notification */}
            {wasOffline && (
              <div className="flex items-center gap-2 text-xs text-green-600">
                <Check className="h-4 w-4" />
                <span>Connection restored</span>
              </div>
            )}
          </div>

          {/* Error message with retry button */}
          {saveError && (
            <div className="flex items-center justify-between bg-red-50 dark:bg-red-900/10 p-3 rounded-md">
              <p className="text-xs text-red-600 flex-1">{saveError}</p>
              {saveStatus === 'error' && retryCount < 3 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={lastAction === 'complete' ? handleMarkCompleted : handleSaveDraft}
                  className="ml-2 h-8 min-h-[44px] min-w-[44px]"
                >
                  Retry
                </Button>
              )}
            </div>
          )}
        </div>
      </CardContent>

      <CardFooter className="flex flex-col space-y-4">
        {/* Action buttons */}
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center space-x-2">
            {!isCompleted ? (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleSaveDraft}
                  disabled={isSaving || !responseText.trim()}
                  className="min-h-[44px] min-w-[44px]"
                >
                  Save Draft
                </Button>

                <Button
                  variant="default"
                  size="sm"
                  onClick={handleMarkCompleted}
                  disabled={isSaving || !responseText.trim()}
                  className="min-h-[44px] min-w-[44px]"
                >
                  Complete Response
                </Button>
              </>
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setIsCompleted(false);
                }}
                className="min-h-[44px] min-w-[44px]"
              >
                Edit Response
              </Button>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleRateQuestion(1)}
              className={`min-h-[44px] min-w-[44px] ${rating === 1 ? 'bg-red-100 dark:bg-red-900/20' : ''}`}
              aria-label="Rate question as poor"
            >
              <ThumbsDown className="h-4 w-4 text-red-500" />
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleRateQuestion(5)}
              className={`min-h-[44px] min-w-[44px] ${rating === 5 ? 'bg-green-100 dark:bg-green-900/20' : ''}`}
              aria-label="Rate question as good"
            >
              <ThumbsUp className="h-4 w-4 text-green-500" />
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={handleRegenerateQuestion}
              title="Generate a new question"
              className="min-h-[44px] min-w-[44px]"
              aria-label="Generate a new question"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Info text */}
        <p className="text-xs text-muted-foreground">
          {isCompleted
            ? "You've completed this question. You can edit your response if needed."
            : "Remember to click 'Complete Response' when you're satisfied with your answer."}
        </p>
      </CardFooter>
    </Card>
  );
}
