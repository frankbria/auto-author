import Link from 'next/link';

/** The three-step path from a summary to written chapters, shown on the book page. */
export function BookWizardSteps({
  bookId,
  summary,
  chapterCount,
}: {
  bookId: string;
  summary?: string;
  chapterCount: number;
}) {
  const hasSummary = !!summary && summary.length >= 30;
  const hasChapters = chapterCount > 0;
  return (
    <div className="mt-8 mb-8">
      <div className="flex flex-col md:flex-row md:items-center gap-4">
        {/* Step 1: Book Summary */}
        <div className="flex items-center gap-3">
          <div className="flex flex-col items-center">
            <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center font-bold">1</div>
            <div className="h-8 w-1 bg-indigo-300/30 md:h-1 md:w-8 md:mx-2 md:my-0 my-2"></div>
          </div>
          <div>
            <div className="font-semibold text-foreground">Book Summary</div>
            <div className="text-xs text-muted-foreground">Describe your book&apos;s main idea and structure</div>
            <Link href={`/dashboard/books/${bookId}/summary`}>
              <button className="mt-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md">
                {hasSummary ? 'Edit Book Summary' : 'Start with Book Summary'}
              </button>
            </Link>
          </div>
        </div>
        {/* Step 2: TOC Generation */}
        <div className="flex items-center gap-3">
          <div className="flex flex-col items-center">
            <div className={`w-8 h-8 rounded-full ${(hasSummary) ? 'bg-indigo-600 text-white' : 'bg-muted text-muted-foreground border border-border'} flex items-center justify-center font-bold`}>2</div>
            <div className="h-8 w-1 bg-indigo-300/30 md:h-1 md:w-8 md:mx-2 md:my-0 my-2"></div>
          </div>
          <div>
            <div className="font-semibold text-foreground">Generate TOC</div>
            <div className="text-xs text-muted-foreground">AI generates a Table of Contents from your summary</div>
            {hasSummary ? (
              hasChapters ? (
                <Link href={`/dashboard/books/${bookId}/edit-toc`}>
                  <button className="mt-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md">
                    Edit TOC
                  </button>
                </Link>
              ) : (
                <Link href={`./generate-toc`}>
                  <button className="mt-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md">
                    Generate TOC
                  </button>
                </Link>
              )
            ) : (
              <button className="mt-2 px-4 py-2 bg-muted text-muted-foreground font-medium rounded-md cursor-not-allowed" disabled>
                Complete Book Summary First
              </button>
            )}
          </div>
        </div>
        {/* Step 3: Write Content */}
        <div className="flex items-center gap-3">
          <div className="flex flex-col items-center">
            <div className={`w-8 h-8 rounded-full ${(hasSummary && hasChapters) ? 'bg-indigo-600 text-white' : 'bg-muted text-muted-foreground border border-border'} flex items-center justify-center font-bold`}>3</div>
          </div>
          <div>
            <div className="font-semibold text-foreground">Write Content</div>
            <div className="text-xs text-muted-foreground">Write and edit your chapter content</div>
            {(hasSummary && hasChapters) ? (
              <div className="mt-2 text-sm text-green-700 dark:text-green-400">
                ✓ Ready to write! Use the tabs below to start writing your chapters.
              </div>
            ) : (
              <button className="mt-2 px-4 py-2 bg-muted text-muted-foreground font-medium rounded-md cursor-not-allowed" disabled>
                {hasSummary ? 'Generate TOC First' : 'Complete Book Summary First'}
              </button>
            )}
          </div>
        </div>
        <div className="flex-1"></div>
      </div>
    </div>
  );
}
