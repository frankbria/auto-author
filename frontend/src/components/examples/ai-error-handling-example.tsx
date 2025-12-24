/**
 * Example Component: AI Error Handling
 *
 * Demonstrates how to use the AI error handling system with:
 * - Cached content fallback
 * - Rate limit handling with countdown
 * - Network error retry
 * - Loading states
 */

'use client';

import { useState } from 'react';
import DOMPurify from 'dompurify';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { HugeiconsIcon } from '@hugeicons/react';
import { SparklesIcon, RefreshIcon, Database01Icon } from '@hugeicons/core-free-icons';
import bookClient from '@/lib/api/bookClient';
import { isFromCache } from '@/lib/api/aiErrorHandler';

interface AIErrorHandlingExampleProps {
  bookId: string;
}

/**
 * Example: TOC Questions Generation with Error Handling
 */
export function TOCQuestionsExample({ bookId }: AIErrorHandlingExampleProps) {
  const [questions, setQuestions] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isFromCachedContent, setIsFromCachedContent] = useState(false);

  const generateQuestions = async () => {
    setIsLoading(true);
    setIsFromCachedContent(false);

    try {
      // Use the error-handling version of the API call
      const result = await bookClient.generateQuestionsWithErrorHandling(
        bookId,
        generateQuestions // Pass retry callback
      );

      // Check if we got cached content
      if (isFromCache(result)) {
        setQuestions(result.data.questions);
        setIsFromCachedContent(true);
        return;
      }

      // Check if we got fresh data
      if (result.data) {
        setQuestions(result.data.questions);
        setIsFromCachedContent(false);
        return;
      }

      // Error occurred - notification already shown by error handler
      // You can add additional UI feedback here if needed
      console.error('Failed to generate questions:', result.error);
    } catch (error) {
      // Handle any unexpected errors
      console.error('Unexpected error generating questions:', error);
      // Error notification is handled by the error handler
    } finally {
      // Always clear loading state
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">TOC Questions</h3>
        <Button
          onClick={generateQuestions}
          disabled={isLoading}
          data-testid="generate-questions-button"
        >
          {isLoading ? (
            <>
              <HugeiconsIcon icon={RefreshIcon} size={16} className="mr-2 animate-spin" aria-hidden="true" />
              Generating...
            </>
          ) : (
            <>
              <HugeiconsIcon icon={SparklesIcon} size={16} className="mr-2" aria-hidden="true" />
              Generate Questions
            </>
          )}
        </Button>
      </div>

      {isFromCachedContent && (
        <Alert className="bg-blue-900/20 border-blue-500">
          <HugeiconsIcon icon={Database01Icon} size={16} aria-hidden="true" />
          <AlertDescription>
            Using previously generated content (AI service temporarily unavailable)
            <Button
              variant="link"
              size="sm"
              onClick={generateQuestions}
              className="ml-2"
            >
              Try generating fresh content
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {questions.length > 0 && (
        <div className="space-y-2">
          {questions.map((question, index) => (
            <div
              key={index}
              className="p-3 bg-zinc-800 rounded-lg border border-zinc-700"
            >
              <p className="text-sm text-zinc-300">{question}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Example: Chapter Draft Generation with Error Handling
 */
export function ChapterDraftExample({ bookId, chapterId }: AIErrorHandlingExampleProps & { chapterId: string }) {
  const [draft, setDraft] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [isFromCachedContent, setIsFromCachedContent] = useState(false);

  const generateDraft = async () => {
    setIsLoading(true);
    setIsFromCachedContent(false);

    try {
      const result = await bookClient.generateChapterDraftWithErrorHandling(
        bookId,
        chapterId,
        {
          question_responses: [
            { question: 'Main topic?', answer: 'Example topic' },
          ],
          writing_style: 'conversational',
          target_length: 2000,
        },
        generateDraft // Retry callback
      );

      if (isFromCache(result)) {
        setDraft(result.data.draft);
        setIsFromCachedContent(true);
        return;
      }

      if (result.data) {
        setDraft(result.data.draft);
        setIsFromCachedContent(false);
        return;
      }

      console.error('Failed to generate draft:', result.error);
    } catch (error) {
      // Handle any unexpected errors
      console.error('Unexpected error generating draft:', error);
      // Error notification is handled by the error handler
    } finally {
      // Always clear loading state
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Chapter Draft</h3>
        <Button
          onClick={generateDraft}
          disabled={isLoading}
          data-testid="generate-draft-button"
        >
          {isLoading ? (
            <>
              <HugeiconsIcon icon={RefreshIcon} size={16} className="mr-2 animate-spin" aria-hidden="true" />
              Generating...
            </>
          ) : (
            <>
              <HugeiconsIcon icon={SparklesIcon} size={16} className="mr-2" aria-hidden="true" />
              Generate Draft
            </>
          )}
        </Button>
      </div>

      {isFromCachedContent && (
        <Alert className="bg-blue-900/20 border-blue-500">
          <HugeiconsIcon icon={Database01Icon} size={16} aria-hidden="true" />
          <AlertDescription>
            Using previously generated draft (AI service temporarily unavailable)
          </AlertDescription>
        </Alert>
      )}

      {draft && (
        <div className="p-4 bg-zinc-800 rounded-lg border border-zinc-700">
          <div className="prose prose-invert max-w-none">
            <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(draft) }} />
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Example: Summary Analysis with Error Handling
 */
export function SummaryAnalysisExample({ bookId }: AIErrorHandlingExampleProps) {
  const [analysis, setAnalysis] = useState<{
    is_ready_for_toc: boolean;
    confidence_score: number;
    analysis: string;
    suggestions: string[];
  } | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isFromCachedContent, setIsFromCachedContent] = useState(false);

  const analyzeSummary = async () => {
    setIsLoading(true);
    setIsFromCachedContent(false);

    try {
      const result = await bookClient.analyzeSummaryWithErrorHandling(
        bookId,
        analyzeSummary
      );

      if (isFromCache(result)) {
        setAnalysis(result.data.analysis);
        setIsFromCachedContent(true);
        return;
      }

      if (result.data) {
        setAnalysis(result.data.analysis);
        setIsFromCachedContent(false);
        return;
      }

      console.error('Failed to analyze summary:', result.error);
    } catch (error) {
      // Handle any unexpected errors
      console.error('Unexpected error analyzing summary:', error);
      // Error notification is handled by the error handler
    } finally {
      // Always clear loading state
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Summary Analysis</h3>
        <Button
          onClick={analyzeSummary}
          disabled={isLoading}
          data-testid="analyze-button"
        >
          {isLoading ? (
            <>
              <HugeiconsIcon icon={RefreshIcon} size={16} className="mr-2 animate-spin" aria-hidden="true" />
              Analyzing...
            </>
          ) : (
            <>
              <HugeiconsIcon icon={SparklesIcon} size={16} className="mr-2" aria-hidden="true" />
              Analyze Summary
            </>
          )}
        </Button>
      </div>

      {isFromCachedContent && (
        <Alert className="bg-blue-900/20 border-blue-500">
          <HugeiconsIcon icon={Database01Icon} size={16} aria-hidden="true" />
          <AlertDescription>
            Using previously generated analysis
          </AlertDescription>
        </Alert>
      )}

      {analysis && (
        <div className="space-y-3">
          <div className="p-4 bg-zinc-800 rounded-lg border border-zinc-700">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">
                Ready for TOC:
              </span>
              <span
                className={`text-sm font-semibold ${
                  analysis.is_ready_for_toc ? 'text-green-500' : 'text-red-500'
                }`}
              >
                {analysis.is_ready_for_toc ? 'Yes' : 'No'}
              </span>
            </div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium">Confidence:</span>
              <span className="text-sm font-semibold">
                {(analysis.confidence_score * 100).toFixed(0)}%
              </span>
            </div>
            <p className="text-sm text-zinc-300 mb-3">{analysis.analysis}</p>

            {analysis.suggestions.length > 0 && (
              <div>
                <p className="text-sm font-medium mb-2">Suggestions:</p>
                <ul className="list-disc list-inside space-y-1">
                  {analysis.suggestions.map((suggestion, index) => (
                    <li key={index} className="text-sm text-zinc-400">
                      {suggestion}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Usage Example:
 *
 * ```tsx
 * import { TOCQuestionsExample, ChapterDraftExample, SummaryAnalysisExample } from '@/components/examples/ai-error-handling-example';
 *
 * function MyComponent() {
 *   const bookId = 'book-123';
 *   const chapterId = 'chapter-456';
 *
 *   return (
 *     <div>
 *       <TOCQuestionsExample bookId={bookId} />
 *       <ChapterDraftExample bookId={bookId} chapterId={chapterId} />
 *       <SummaryAnalysisExample bookId={bookId} />
 *     </div>
 *   );
 * }
 * ```
 *
 * Key Features:
 * - Automatic error notifications with appropriate messages
 * - Cached content fallback when AI service is unavailable
 * - Rate limit handling with countdown timer
 * - Network error retry support
 * - Loading states for better UX
 * - Visual indicators for cached content
 */
