export default function ReadinessChecker() {
  return (
    <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-8">
      <div className="flex flex-col items-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500 mb-6"></div>
        
        <h2 className="text-xl font-semibold text-zinc-100 mb-3">
          Analyzing Your Summary
        </h2>
          <p className="text-zinc-400 text-center mb-6 max-w-md">
          We&apos;re checking if your book summary contains enough detail to generate a comprehensive table of contents.
        </p>
        
        <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-4 w-full max-w-md">
          <h3 className="text-zinc-300 font-medium mb-3">What we&apos;re analyzing:</h3>
          <ul className="text-zinc-400 text-sm space-y-2">
            <li className="flex items-center">
              <div className="w-2 h-2 bg-indigo-500 rounded-full mr-3"></div>
              Content depth and detail
            </li>
            <li className="flex items-center">
              <div className="w-2 h-2 bg-indigo-500 rounded-full mr-3"></div>
              Key topics and themes
            </li>
            <li className="flex items-center">
              <div className="w-2 h-2 bg-indigo-500 rounded-full mr-3"></div>
              Structural elements
            </li>
            <li className="flex items-center">
              <div className="w-2 h-2 bg-indigo-500 rounded-full mr-3"></div>
              Word count and coverage
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
