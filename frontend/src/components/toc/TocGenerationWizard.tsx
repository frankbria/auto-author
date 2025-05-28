'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { bookClient } from '@/lib/api/bookClient';
import { 
  WizardStep, 
  WizardState, 
  QuestionResponse
} from '@/types/toc';
import ReadinessChecker from './ReadinessChecker';
import NotReadyMessage from './NotReadyMessage';
import ClarifyingQuestions from './ClarifyingQuestions';
import TocGenerating from './TocGenerating';
import TocReview from './TocReview';
import ErrorDisplay from './ErrorDisplay';

interface TocGenerationWizardProps {
  bookId: string;
}

export default function TocGenerationWizard({ bookId }: TocGenerationWizardProps) {
  const router = useRouter();
  const [wizardState, setWizardState] = useState<WizardState>({
    step: WizardStep.CHECKING_READINESS,
    questionResponses: [],
    isLoading: true
  });

  const generateQuestions = useCallback(async () => {
    try {
      setWizardState(prev => ({ ...prev, isLoading: true }));
      const response = await bookClient.generateQuestions(bookId);
      
      setWizardState(prev => ({
        ...prev,
        step: WizardStep.ASKING_QUESTIONS,
        questions: response.questions,
        isLoading: false
      }));
    } catch (error) {
      console.error('Error generating questions:', error);
      setWizardState(prev => ({
        ...prev,
        step: WizardStep.ERROR,
        error: 'Failed to generate clarifying questions. Please try again.',
        isLoading: false
      }));
    }
  }, [bookId]);
  const checkTocReadiness = useCallback(async () => {
    try {
      setWizardState(prev => ({ ...prev, isLoading: true }));
      
      // First, analyze the summary using AI to get readiness assessment
      try {
        console.log('Analyzing summary with AI...');
        await bookClient.analyzeSummary(bookId);
        console.log('Summary analysis completed');
      } catch (analysisError) {
        console.warn('Summary analysis failed, proceeding with basic check:', analysisError);
        // Continue with readiness check even if analysis fails
      }
      
      // Then check readiness status (which will now include analysis results)
      const readiness = await bookClient.checkTocReadiness(bookId);
      
      if (readiness.meets_minimum_requirements) {
        // If ready, proceed to generate questions
        await generateQuestions();
      } else {
        setWizardState(prev => ({
          ...prev,
          step: WizardStep.NOT_READY,
          readiness,
          isLoading: false
        }));
      }
    } catch (error) {
      console.error('Error checking TOC readiness:', error);
      setWizardState(prev => ({
        ...prev,
        step: WizardStep.ERROR,
        error: 'Failed to check if your summary is ready for TOC generation. Please try again.',
        isLoading: false
      }));
    }
  }, [bookId, generateQuestions]);

  // Check if the book summary is ready for TOC generation
  useEffect(() => {
    checkTocReadiness();
  }, [checkTocReadiness]);

  const handleQuestionSubmit = async (responses: QuestionResponse[]) => {
    try {
      setWizardState(prev => ({
        ...prev,
        step: WizardStep.GENERATING,
        questionResponses: responses,
        isLoading: true
      }));

      const result = await bookClient.generateToc(bookId, responses);
      
      // Ensure chapters have all required TocChapter fields
      const transformedResult = {
        ...result,
        toc: {
          ...result.toc,
          chapters: result.toc.chapters.map((chapter: any) => ({
            status: chapter.status ?? 'draft',
            word_count: chapter.word_count ?? 0,
            estimated_reading_time: chapter.estimated_reading_time ?? 0,
            ...chapter,
            subchapters: chapter.subchapters?.map((sub: any) => ({
              status: sub.status ?? 'draft',
              word_count: sub.word_count ?? 0,
              estimated_reading_time: sub.estimated_reading_time ?? 0,
              ...sub,
            })) ?? [],
          })),
        },
      };

      setWizardState(prev => ({
        ...prev,
        step: WizardStep.REVIEW,
        generatedToc: transformedResult,
        isLoading: false
      }));
    } catch (error) {
      console.error('Error generating TOC:', error);
      setWizardState(prev => ({
        ...prev,
        step: WizardStep.ERROR,
        error: 'Failed to generate table of contents. Please try again.',
        isLoading: false
      }));
    }
  };

  const handleAcceptToc = async () => {
    try {
      if (!wizardState.generatedToc?.toc) return;
      
      setWizardState(prev => ({ ...prev, isLoading: true }));
      
      // Save the TOC to the backend
      await bookClient.updateToc(bookId, wizardState.generatedToc.toc);
      
      // Navigate to the edit TOC page
      router.push(`/dashboard/books/${bookId}/edit-toc`);
    } catch (error) {
      console.error('Error saving TOC:', error);
      setWizardState(prev => ({
        ...prev,
        error: 'Failed to save table of contents. Please try again.',
        isLoading: false
      }));
    }
  };

  const handleRegenerateToc = async () => {
    try {
      setWizardState(prev => ({
        ...prev,
        step: WizardStep.GENERATING,
        isLoading: true,
        error: undefined
      }));

      const result = await bookClient.generateToc(bookId, wizardState.questionResponses);
      
      // Ensure chapters have all required TocChapter fields
      const transformedResult = {
        ...result,
        toc: {
          ...result.toc,
          chapters: result.toc.chapters.map((chapter: any) => ({
            status: chapter.status ?? 'draft',
            word_count: chapter.word_count ?? 0,
            estimated_reading_time: chapter.estimated_reading_time ?? 0,
            ...chapter,
            subchapters: chapter.subchapters?.map((sub: any) => ({
              status: sub.status ?? 'draft',
              word_count: sub.word_count ?? 0,
              estimated_reading_time: sub.estimated_reading_time ?? 0,
              ...sub,
            })) ?? [],
          })),
        },
      };

      setWizardState(prev => ({
        ...prev,
        step: WizardStep.REVIEW,
        generatedToc: transformedResult,
        isLoading: false
      }));
    } catch (error) {
      console.error('Error regenerating TOC:', error);
      setWizardState(prev => ({
        ...prev,
        step: WizardStep.ERROR,
        error: 'Failed to regenerate table of contents. Please try again.',
        isLoading: false
      }));
    }
  };
  const handleRetry = () => {
    setWizardState({
      step: WizardStep.CHECKING_READINESS,
      questionResponses: [],
      isLoading: true
    });
    checkTocReadiness();
  };

  const renderCurrentStep = () => {
    switch (wizardState.step) {      case WizardStep.CHECKING_READINESS:
        return <ReadinessChecker />;
      
      case WizardStep.NOT_READY:
        return (
          <NotReadyMessage 
            readiness={wizardState.readiness!} 
            onRetry={handleRetry}
            bookId={bookId}
          />
        );
        case WizardStep.ASKING_QUESTIONS:
        return (
          <ClarifyingQuestions 
            questions={wizardState.questions!}
            onSubmit={handleQuestionSubmit}
            isLoading={wizardState.isLoading}
            bookId={bookId}
          />
        );
      
      case WizardStep.GENERATING:
        return <TocGenerating />;
      
      case WizardStep.REVIEW:
        return (
          <TocReview 
            tocResult={wizardState.generatedToc!}
            onAccept={handleAcceptToc}
            onRegenerate={handleRegenerateToc}
            isLoading={wizardState.isLoading}
          />
        );
      
      case WizardStep.ERROR:
        return (
          <ErrorDisplay 
            error={wizardState.error!}
            onRetry={handleRetry}
          />
        );
      
      default:
        return null;
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-zinc-100 mb-3">Generate Table of Contents</h1>
        <p className="text-zinc-400">
          Our AI will analyze your summary and guide you through creating a structured table of contents for your book.
        </p>
      </div>

      {/* Progress indicator */}
      <div className="mb-8">
        <div className="flex items-center justify-between text-sm text-zinc-400 mb-2">
          <span>Step {getStepNumber(wizardState.step)} of 4</span>
          <span>{getStepTitle(wizardState.step)}</span>
        </div>
        <div className="w-full bg-zinc-700 rounded-full h-2">
          <div 
            className="bg-indigo-600 h-2 rounded-full transition-all duration-300" 
            style={{ width: `${getProgressPercentage(wizardState.step)}%` }}
          ></div>
        </div>
      </div>

      {renderCurrentStep()}
    </div>
  );
}

function getStepNumber(step: WizardStep): number {
  switch (step) {
    case WizardStep.CHECKING_READINESS:
    case WizardStep.NOT_READY:
      return 1;
    case WizardStep.ASKING_QUESTIONS:
      return 2;
    case WizardStep.GENERATING:
      return 3;
    case WizardStep.REVIEW:
      return 4;
    default:
      return 1;
  }
}

function getStepTitle(step: WizardStep): string {
  switch (step) {
    case WizardStep.CHECKING_READINESS:
      return 'Checking readiness';
    case WizardStep.NOT_READY:
      return 'Summary needs improvement';
    case WizardStep.ASKING_QUESTIONS:
      return 'Clarifying questions';
    case WizardStep.GENERATING:
      return 'Generating TOC';
    case WizardStep.REVIEW:
      return 'Review & approve';
    case WizardStep.ERROR:
      return 'Error occurred';
    default:
      return 'Processing';
  }
}

function getProgressPercentage(step: WizardStep): number {
  switch (step) {
    case WizardStep.CHECKING_READINESS:
    case WizardStep.NOT_READY:
      return 25;
    case WizardStep.ASKING_QUESTIONS:
      return 50;
    case WizardStep.GENERATING:
      return 75;
    case WizardStep.REVIEW:
      return 100;
    default:
      return 25;
  }
}
