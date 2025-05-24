interface ErrorDisplayProps {
  error: string;
  onRetry: () => void;
}

export default function ErrorDisplay({ error, onRetry }: ErrorDisplayProps) {
  return (
    <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-8">
      <div className="text-center">
        <div className="w-16 h-16 bg-red-900/20 border border-red-700 rounded-full flex items-center justify-center mx-auto mb-6">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        
        <h2 className="text-xl font-semibold text-zinc-100 mb-3">
          Something Went Wrong
        </h2>
        
        <p className="text-zinc-400 mb-6 max-w-md mx-auto">
          {error}
        </p>
        
        <button
          onClick={onRetry}
          className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md transition-colors flex items-center mx-auto"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
          </svg>
          Try Again
        </button>
        
        <div className="mt-8 bg-zinc-800/50 border border-zinc-700 rounded-lg p-4 max-w-md mx-auto">
          <h4 className="text-zinc-300 font-medium mb-2">Possible solutions:</h4>
          <ul className="text-zinc-400 text-sm list-disc list-inside space-y-1">
            <li>Check your internet connection</li>
            <li>Wait a moment and try again</li>
            <li>Refresh the page if the problem persists</li>
            <li>Contact support if issues continue</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
