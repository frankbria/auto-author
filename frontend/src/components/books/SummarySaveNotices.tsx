import { Button } from '@/components/ui/button';

/**
 * What the summary page says about a save that failed (#832): now, and on the
 * visit after, when the text that was not saved is offered back.
 */
export function SummarySaveNotices({
  saveFailure,
  unsavedDraft,
  onRestore,
  onDiscard,
}: {
  /** A save failed on this visit. `kept` is whether the text is at least in this browser. */
  saveFailure: { kept: boolean } | null;
  /** Text from an earlier visit whose save failed. */
  unsavedDraft: string | null;
  onRestore: () => void;
  onDiscard: () => void;
}) {
  return (
    <>
      {/* role="alert": the writer's text is not on the server, which is worth
          interrupting for. */}
      {saveFailure && (
        <div
          role="alert"
          className="p-4 mb-6 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-300 dark:border-red-700 text-red-700 dark:text-red-400"
        >
          {saveFailure.kept
            ? 'Your summary could not be saved. It is kept on this device, and saving is tried again when you change it.'
            : 'Your summary could not be saved, and it could not be kept on this device either. Copy it somewhere safe before leaving this page.'}
        </div>
      )}
      {unsavedDraft !== null && (
        <div className="p-4 mb-6 rounded-lg bg-yellow-500/10 border border-yellow-500/20 text-yellow-700 dark:text-yellow-400 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <span>A summary you wrote on this device was not saved. The one below is the last that was.</span>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={onRestore}>
              Restore it
            </Button>
            <Button size="sm" variant="ghost" onClick={onDiscard}>
              Discard it
            </Button>
          </div>
        </div>
      )}
    </>
  );
}
