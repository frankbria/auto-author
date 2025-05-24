import { useState } from 'react';
import { QuestionResponse } from '@/types/toc';

interface ClarifyingQuestionsProps {
  questions: string[];
  onSubmit: (responses: QuestionResponse[]) => void;
  isLoading: boolean;
}

export default function ClarifyingQuestions({ questions, onSubmit, isLoading }: ClarifyingQuestionsProps) {
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);

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

  const handleSubmit = () => {
    const questionResponses: QuestionResponse[] = questions.map((question, index) => ({
      question,
      answer: responses[index] || ''
    }));
    
    onSubmit(questionResponses);
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

      <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-6 mb-6">
        <h3 className="text-zinc-100 font-medium mb-4 text-lg">
          {currentQuestion}
        </h3>
        
        <textarea
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
