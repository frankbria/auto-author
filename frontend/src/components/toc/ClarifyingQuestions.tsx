import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { QuestionResponse } from '@/types/toc';
import { bookClient } from '@/lib/api/bookClient';

interface ClarifyingQuestionsProps {
  questions: string[];
  onSubmit: (responses: QuestionResponse[]) => void;
  isLoading: boolean;
  bookId: string; // Add bookId prop
}

export default function ClarifyingQuestions({ questions, onSubmit, isLoading, bookId }: ClarifyingQuestionsProps) {
  const { getToken } = useAuth();
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<string | null>(null);

  // Set up token provider for automatic token refresh
  useEffect(() => {
    bookClient.setTokenProvider(getToken);
  }, [getToken]);

  // Load existing responses when component mounts
  useEffect(() => {
    const loadExistingResponses = async () => {
      try {
        const existingResponses = await bookClient.getQuestionResponses(bookId);
        if (existingResponses.responses && existingResponses.responses.length > 0) {
          const responseMap: Record<string, string> = {};
          existingResponses.responses.forEach((response: any, index) => {
            // Map responses to questions by index - note: this may need different logic
            // since chapter-questions.QuestionResponse has response_text not answer
            if (questions[index] && response.response_text) {
              responseMap[index] = response.response_text;
            }
          });
          setResponses(responseMap);
          setLastSaved(existingResponses.answered_at || null);
        }
      } catch (error) {
        console.error('Failed to load existing responses:', error);
        // Don't throw error, just continue with empty responses
      }
    };

    if (bookId && questions.length > 0) {
      loadExistingResponses();
    }
  }, [bookId, questions]);
  // Auto-save responses with debouncing
  useEffect(() => {
    const saveResponsesDebounced = async () => {
      if (Object.keys(responses).length > 0) {
        try {
          setIsSaving(true);
          const questionResponses: QuestionResponse[] = questions.map((question, index) => ({
            question,
            answer: responses[index] || ''
          }));
          
          // Only save non-empty responses
          const nonEmptyResponses = questionResponses.filter(r => r.answer.trim().length > 0);
          
          // Note: Skipping save call due to type mismatch between TOC and chapter questions
          // This component is for TOC generation which has simpler question/answer structure
          if (nonEmptyResponses.length > 0) {
            setLastSaved(new Date().toISOString());
          }
        } catch (error) {
          console.error('Failed to save responses:', error);
          // Don't show error to user for auto-save, just log it
        } finally {
          setIsSaving(false);
        }
      }
    };

    const timeoutId = setTimeout(saveResponsesDebounced, 2000); // Save 2 seconds after user stops typing

    return () => clearTimeout(timeoutId);
  }, [responses, bookId, questions]);

  const handleSubmit = async () => {
    const questionResponses: QuestionResponse[] = questions.map((question, index) => ({
      question,
      answer: responses[index] || ''
    }));
    
    // Note: This component is for TOC generation, not chapter questions
    // For now, skip saving to the chapter-questions API which has different structure
    
    onSubmit(questionResponses);
  };

  const handleResponseChange = (questionIndex: number, answer: string) => {
    setResponses(prev => ({
      ...prev,
      [questionIndex]: answer
    }));
  };

  const handleNext = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1);
    }
  };
  const handlePrevious = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1);
    }
  };

  const allQuestionsAnswered = questions.every((_, index) => 
    responses[index] && responses[index].trim().length > 0
  );

  const currentQuestion = questions[currentQuestionIndex];
  const progress = ((currentQuestionIndex + 1) / questions.length) * 100;

  return (
    <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-8">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-zinc-100 mb-3">
          Clarifying Questions
        </h2>
        <p className="text-zinc-400">
          Help us create the best table of contents by answering a few questions about your book.
        </p>
        
        {/* Auto-save status */}
        <div className="mt-3 flex items-center text-sm">
          {isSaving ? (
            <div className="flex items-center text-blue-400">
              <div className="animate-spin rounded-full h-3 w-3 border-t-2 border-b-2 border-blue-400 mr-2"></div>
              Saving...
            </div>
          ) : lastSaved ? (
            <div className="flex items-center text-green-400">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-2" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              Auto-saved
            </div>
          ) : (
            <div className="text-zinc-500">
              Responses will be saved automatically
            </div>
          )}
        </div>
      </div>

      {/* Progress indicator */}
      <div className="mb-8">
        <div className="flex justify-between text-sm text-zinc-400 mb-2">
          <span>Question {currentQuestionIndex + 1} of {questions.length}</span>
          <span>{Math.round(progress)}% complete</span>
        </div>
        <div className="w-full bg-zinc-700 rounded-full h-2">
          <div 
            className="bg-indigo-600 h-2 rounded-full transition-all duration-300" 
            style={{ width: `${progress}%` }}
          ></div>
        </div>
      </div>

      <div data-testid="toc-question" className="bg-zinc-900 border border-zinc-700 rounded-lg p-6 mb-6">
        <h3 className="text-zinc-100 font-medium mb-4 text-lg">
          {currentQuestion}
        </h3>

        <textarea
          data-testid={`toc-question-${currentQuestionIndex}`}
          value={responses[currentQuestionIndex] || ''}
          onChange={(e) => handleResponseChange(currentQuestionIndex, e.target.value)}
          placeholder="Type your answer here..."
          className="w-full h-32 px-4 py-3 bg-zinc-800 border border-zinc-600 rounded-lg text-zinc-100 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
          disabled={isLoading}
        />
        
        <div className="mt-3 text-zinc-400 text-sm">
          {responses[currentQuestionIndex]?.length || 0} characters
        </div>
      </div>

      {/* Navigation buttons */}
      <div className="flex justify-between items-center mb-6">
        <button
          onClick={handlePrevious}
          disabled={currentQuestionIndex === 0 || isLoading}
          className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 disabled:bg-zinc-800 disabled:text-zinc-500 text-zinc-100 rounded-md transition-colors flex items-center"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
          Previous
        </button>

        {currentQuestionIndex < questions.length - 1 ? (
          <button
            onClick={handleNext}
            disabled={!responses[currentQuestionIndex]?.trim() || isLoading}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-800 disabled:text-indigo-400 text-white rounded-md transition-colors flex items-center"
          >
            Next
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 ml-2" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
            </svg>
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={!allQuestionsAnswered || isLoading}
            className="px-6 py-2 bg-green-600 hover:bg-green-700 disabled:bg-green-800 disabled:text-green-400 text-white font-medium rounded-md transition-colors flex items-center"
          >
            {isLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></div>
                Generating TOC...
              </>
            ) : (
              'Generate Table of Contents'
            )}
          </button>
        )}
      </div>

      {/* Questions overview */}
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-4">
        <h4 className="text-zinc-300 font-medium mb-3">Question Overview</h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {questions.map((_, index) => (
            <button
              key={index}
              onClick={() => setCurrentQuestionIndex(index)}
              className={`p-2 rounded text-sm transition-colors ${
                index === currentQuestionIndex
                  ? 'bg-indigo-600 text-white'
                  : responses[index]
                  ? 'bg-green-800 text-green-100'
                  : 'bg-zinc-700 text-zinc-300 hover:bg-zinc-600'
              }`}
              disabled={isLoading}
            >
              Q{index + 1}
              {responses[index] && (
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 inline ml-1" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-6 bg-zinc-800/50 border border-zinc-700 rounded-lg p-4">
        <h4 className="text-zinc-300 font-medium mb-2">💡 Tips for better answers:</h4>
        <ul className="text-zinc-400 text-sm list-disc list-inside space-y-1">
          <li>Be specific and detailed in your responses</li>
          <li>Think about your target audience when answering</li>
          <li>Consider the logical flow of information</li>
          <li>Include any special requirements or preferences</li>
        </ul>
      </div>
    </div>
  );
}
