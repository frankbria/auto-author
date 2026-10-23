export function BookStatsPanel({
  progress,
  chapters,
  onExport,
}: {
  progress: number;
  chapters: { wordCount: number; completed: boolean }[];
  onExport: () => void;
}) {
  return (
  <div className="bg-card border border-border p-5 rounded-lg">
    <h2 className="text-xl font-semibold text-foreground mb-4">Book Stats</h2>
    <div className="space-y-3">
      <div>
        <div className="text-sm text-muted-foreground mb-1">Overall Progress</div>
        <div className="flex items-center gap-2">
          <div
            className="flex-1 bg-muted rounded-full h-2"
            role="progressbar"
            aria-label="Overall progress"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progress}
          >
            <div
              className="bg-indigo-600 h-2 rounded-full"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          <span className="text-foreground">{progress}%</span>
        </div>
      </div>
      <div className="pt-2">
        <div className="text-sm text-muted-foreground mb-1">Chapters</div>
        <div className="text-foreground font-medium">{chapters.length}</div>
      </div>
      <div className="pt-2">
        <div className="text-sm text-muted-foreground mb-1">Total Word Count</div>
        <div className="text-foreground font-medium">
          {chapters.reduce((sum, chapter) => sum + chapter.wordCount, 0).toLocaleString()}
        </div>
      </div>
      <div className="pt-2">
        <div className="text-sm text-muted-foreground mb-1">Completed Chapters</div>
        <div className="text-foreground font-medium">
          {chapters.filter(ch => ch.completed).length} of {chapters.length}
        </div>
      </div>
    </div>
    <div className="mt-6 pt-4 border-t border-border">
      <button
        onClick={onExport}
        className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md transition-all"
      >
        Export Book
      </button>
    </div>
  </div>
  );
}
