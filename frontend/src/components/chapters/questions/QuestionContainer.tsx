'use client';

import { useState, useEffect } from 'react';
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
import { useMediaQuery } from '@/hooks/use-media-query';

interface QuestionContainerProps {
  bookId: string;
  chapterId: string;
  chapterTitle: string;
  onResponseSaved?: () => void; // Optional callback when a response is saved
}

export default function QuestionContainer({ 
  bookId, 
  chapterId,
  chapterTitle,
  onResponseSaved: parentResponseSaved
}: QuestionContainerProps) {
  const { toast } = useToast();
  
  // State
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [progress, setProgress] = useState<QuestionProgressResponse | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  
  const isMobile = useMediaQuery('(max-width: 767px)');
  const isTablet = useMediaQuery('(min-width: 768px) and (max-width: 1023px)');
  const isDesktop = useMediaQuery('(min-width: 1024px)');
  
  // Fetch questions on initial load
  useEffect(() => {
    const fetchQuestions = async () => {
      try {
        setLoading(true);
        const response = await bookClient.getChapterQuestions(bookId, chapterId);
        if (response.questions.length > 0) {
          setQuestions(response.questions);
          await fetchProgress();
        }
      } catch (err) {
        console.error('Error fetching questions:', err);
        setError('Failed to load questions. Please try again.');
      } finally {
        setLoading(false);
      }
    };
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
  
  // Navigation handlers
  const handleNextQuestion = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1);
    }
  };
  
  const handlePreviousQuestion = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1);
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
          onGenerate={handleGenerateQuestions}
          isGenerating={isGenerating}
          error={error}
        />
      </div>
    );
  }
  
  // Show loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="space-y-2 text-center">
          <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full mx-auto"></div>
          <p className="text-sm text-muted-foreground">Loading questions...</p>
        </div>
      </div>
    );
  }
  
  // Show the current question
  const currentQuestion = questions[currentQuestionIndex];

  return (
    <main
      className={`space-y-6 p-4 ${isMobile ? 'mobile-layout' : isTablet ? 'tablet-layout' : isDesktop ? 'desktop-layout' : ''}`}
      role="main"
      aria-label="Chapter questions interface"
      data-testid="question-container"
    >
      {/* Progress bar */}
      {progress && (
        <QuestionProgress 
          progress={progress}
          currentIndex={currentQuestionIndex}
          totalQuestions={questions.length}
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
      
      {/* Error display */}
      {error && (
        <div className="bg-destructive/10 p-4 rounded-md text-destructive">
          <p>{error}</p>
        </div>
      )}
    </main>
  );
}
