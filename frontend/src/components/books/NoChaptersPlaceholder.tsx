import Link from 'next/link';

export function NoChaptersPlaceholder({ hasSummary }: { hasSummary: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center h-64 text-center">
      <div className="mb-4">
        <svg className="h-16 w-16 text-muted-foreground mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
        </svg>
        <h3 className="text-xl font-medium text-foreground mb-2">No chapters yet</h3>
        <p className="text-muted-foreground text-sm max-w-md">
          Complete your book summary and generate a Table of Contents to start writing chapters.
        </p>
      </div>
      {hasSummary ? (
        <Link href={`./generate-toc`}>
          <button className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md">
            Generate Table of Contents
          </button>
        </Link>
      ) : (
        <Link href={`./summary`}>
          <button className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md">
            Complete Book Summary
          </button>
        </Link>
      )}
    </div>
  );
}
