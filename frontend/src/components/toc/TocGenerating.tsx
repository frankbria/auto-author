import { useEffect, useMemo } from 'react';
import { LoadingStateManager } from '@/components/loading';
import { createProgressTracker } from '@/lib/loading';

export default function TocGenerating() {
  const steps = useMemo(() => [
    "Analyzing your responses...",
    "Identifying key themes and topics...",
    "Structuring chapters and sections...",
    "Creating subchapter hierarchies...",
    "Optimizing content flow...",
    "Finalizing table of contents..."
  ], []);

  // Use the progress tracker for realistic time estimates
  const getProgress = useMemo(() => createProgressTracker('toc.generation'), []);
  const { progress, estimatedTimeRemaining } = getProgress();

  // Calculate current step based on progress
  const currentStep = Math.floor((progress / 100) * steps.length);

  return (
    <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-8">
      {/* New LoadingStateManager with progress and time estimate */}
      <LoadingStateManager
        isLoading={true}
        operation="Generating Your Table of Contents"
        progress={progress}
        estimatedTime={estimatedTimeRemaining}
        message="Our AI is analyzing your responses and creating a comprehensive table of contents tailored to your book's content and structure."
      />

      <div className="flex flex-col items-center mt-8">
        {/* Current step */}
        <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-4 w-full max-w-md mb-6">
          <p className="text-zinc-300 text-center font-medium">
            {steps[currentStep] || steps[steps.length - 1]}
          </p>
        </div>

        {/* Process steps */}
        <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-6 w-full max-w-lg">
          <h3 className="text-zinc-300 font-medium mb-4 text-center">AI Processing Steps</h3>
          <div className="space-y-3">
            {steps.map((step, index) => (
              <div key={index} className="flex items-center">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center mr-3 ${
                  index < currentStep
                    ? 'bg-green-600'
                    : index === currentStep
                    ? 'bg-indigo-600'
                    : 'bg-zinc-700'
                }`}>
                  {index < currentStep ? (
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-white" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  ) : index === currentStep ? (
                    <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                  ) : (
                    <span className="text-zinc-400 text-xs">{index + 1}</span>
                  )}
                </div>
                <span className={`text-sm ${
                  index <= currentStep ? 'text-zinc-300' : 'text-zinc-500'
                }`}>
                  {step}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-8 bg-zinc-800/50 border border-zinc-700 rounded-lg p-4 w-full max-w-lg">
          <h4 className="text-zinc-300 font-medium mb-2 text-center">🤖 What&apos;s happening:</h4>
          <ul className="text-zinc-400 text-sm space-y-1">
            <li>• Analyzing thematic patterns in your responses</li>
            <li>• Creating logical chapter progressions</li>
            <li>• Ensuring balanced content distribution</li>
            <li>• Optimizing for reader engagement and flow</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
