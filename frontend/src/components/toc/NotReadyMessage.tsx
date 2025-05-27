import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { TocReadiness } from '@/types/toc';
import { bookClient } from '@/lib/api/bookClient';

interface NotReadyMessageProps {
  readiness: TocReadiness;
  onRetry: () => void;
  bookId: string;
}

export default function NotReadyMessage({ readiness, onRetry, bookId }: NotReadyMessageProps) {
  const router = useRouter();
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleGoToSummary = () => {
    router.push(`/dashboard/books/${bookId}/summary`);
  };

  const handleAnalyzeSummary = async () => {
    try {
      setIsAnalyzing(true);
      console.log('Running fresh analysis on summary...');
      await bookClient.analyzeSummary(bookId);
      console.log('Analysis completed, refreshing readiness check...');
      onRetry(); // This will trigger a fresh readiness check
    } catch (error) {
      console.error('Error analyzing summary:', error);
      // Still call onRetry to refresh the view
      onRetry();
    } finally {
      setIsAnalyzing(false);
    }
  };



  return (
    <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-8">
      <div className="text-center mb-6">
        <div className="w-16 h-16 bg-yellow-900/20 border border-yellow-700 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 15.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
        
        <h2 className="text-xl font-semibold text-zinc-100 mb-3">
          Summary Needs More Detail
        </h2>
        
        <p className="text-zinc-400 mb-6">
          Your book summary needs more detail before we can generate a comprehensive table of contents.
        </p>
      </div>

      <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-6 mb-6">
        <h3 className="text-zinc-300 font-medium mb-4">Analysis Results</h3>
        
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <span className="text-zinc-400">Confidence Score</span>
            <span className="text-zinc-100 font-medium">{Math.round(readiness.confidence_score * 100)}%</span>
          </div>
            <div className="flex justify-between items-center">
            <span className="text-zinc-400">Word Count</span>
            <span className="text-zinc-100 font-medium">
              {readiness.word_count ? readiness.word_count.toLocaleString() : 'N/A'}
            </span>
          </div>
          
          <div className="flex justify-between items-center">
            <span className="text-zinc-400">Meets Requirements</span>
            <span className={`font-medium ${readiness.meets_minimum_requirements ? 'text-green-400' : 'text-red-400'}`}>
              {readiness.meets_minimum_requirements ? 'Yes' : 'No'}
            </span>
          </div>
        </div>

        <div className="mt-6 pt-6 border-t border-zinc-700">
          <h4 className="text-zinc-300 font-medium mb-3">AI Analysis</h4>
          <p className="text-zinc-400 text-sm mb-4">{readiness.analysis}</p>
          
          {readiness.suggestions.length > 0 && (
            <>
              <h4 className="text-zinc-300 font-medium mb-3">Suggestions for Improvement</h4>
              <ul className="text-zinc-400 text-sm space-y-2">
                {readiness.suggestions.map((suggestion, index) => (
                  <li key={index} className="flex items-start">
                    <div className="w-2 h-2 bg-indigo-500 rounded-full mr-3 mt-2 flex-shrink-0"></div>
                    {suggestion}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>      <div className="flex flex-col sm:flex-row gap-4">
        <button
          onClick={handleGoToSummary}
          className="flex-1 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md transition-colors"
        >
          Improve Summary
        </button>
        
        <button
          onClick={handleAnalyzeSummary}
          disabled={isAnalyzing}
          className="flex-1 px-6 py-3 bg-green-600 hover:bg-green-700 disabled:bg-green-800 disabled:opacity-50 text-white font-medium rounded-md transition-colors"
        >
          {isAnalyzing ? 'Analyzing...' : 'Re-analyze Summary'}
        </button>
        
        <button
          onClick={onRetry}
          className="flex-1 px-6 py-3 bg-zinc-700 hover:bg-zinc-600 text-zinc-100 font-medium rounded-md transition-colors"
        >
          Check Again
        </button>
      </div>

      <div className="mt-6 bg-zinc-800/50 border border-zinc-700 rounded-lg p-4">
        <h4 className="text-zinc-300 font-medium mb-2">💡 Tips for a better summary:</h4>
        <ul className="text-zinc-400 text-sm list-disc list-inside space-y-1">
          <li>Include key themes and main topics you want to cover</li>
          <li>Describe the target audience and book&apos;s purpose</li>
          <li>Outline major concepts or storylines</li>
          <li>Add details about structure and approach</li>
          <li>Aim for at least 500-1000 words for comprehensive coverage</li>
        </ul>
      </div>
    </div>
  );
}
