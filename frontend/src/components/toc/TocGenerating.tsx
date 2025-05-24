import { useState, useEffect, useMemo } from 'react';

export default function TocGenerating() {
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);

  const steps = useMemo(() => [
    "Analyzing your responses...",
    "Identifying key themes and topics...",
    "Structuring chapters and sections...",
    "Creating subchapter hierarchies...",
    "Optimizing content flow...",
    "Finalizing table of contents..."
  ], []);

  useEffect(() => {
    const interval = setInterval(() => {
      setProgress(prev => {
        const newProgress = Math.min(prev + 2, 95);
        const stepIndex = Math.floor((newProgress / 100) * steps.length);
        setCurrentStep(stepIndex);
        return newProgress;
      });
    }, 200);

    return () => clearInterval(interval);
  }, [steps]);

  return (
    <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-8">
      <div className="flex flex-col items-center">
        <div className="relative mb-8">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-indigo-500"></div>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-10 h-10 bg-zinc-800 rounded-full flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
          </div>
        </div>

        <h2 className="text-xl font-semibold text-zinc-100 mb-3">
          Generating Your Table of Contents
        </h2>
          <p className="text-zinc-400 text-center mb-8 max-w-md">
          Our AI is analyzing your responses and creating a comprehensive table of contents tailored to your book&apos;s content and structure.
        </p>

        {/* Progress bar */}
        <div className="w-full max-w-md mb-6">
          <div className="flex justify-between text-sm text-zinc-400 mb-2">
            <span>Progress</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-zinc-700 rounded-full h-3">
            <div 
              className="bg-gradient-to-r from-indigo-600 to-purple-600 h-3 rounded-full transition-all duration-300" 
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>

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
