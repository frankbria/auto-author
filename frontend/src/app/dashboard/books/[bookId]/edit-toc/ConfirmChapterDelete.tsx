'use client';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import bookClient from '@/lib/api/bookClient';

export type ChapterNode = { id: string; title: string; word_count?: number; children: ChapterNode[] };

/** What deleting a chapter loses once the TOC is saved. `answers` is null when they could not be counted. */
export type PendingDelete = { chapter: ChapterNode; words: number; answers: number | null };

const withSubchapters = (chapter: ChapterNode): ChapterNode[] => [chapter, ...chapter.children.flatMap(withSubchapters)];

const plural = (n: number, one: string) => `${n.toLocaleString('en-US')} ${n === 1 ? one : `${one}s`}`;

/**
 * Since #755 a saved TOC without a chapter also deletes that chapter's
 * questions and answers (#906). Only chapters the server has stored can have
 * answers, so a chapter added on this page costs no request.
 */
export async function whatDeletingLoses(
  bookId: string,
  chapter: ChapterNode,
  storedIds: Set<string>
): Promise<PendingDelete> {
  const chapters = withSubchapters(chapter);
  const words = chapters.reduce((n, c) => n + (c.word_count ?? 0), 0);
  let answers: number | null;
  try {
    const progress = await Promise.all(
      chapters.filter((c) => storedIds.has(c.id)).map((c) => bookClient.getChapterQuestionProgress(bookId, c.id))
    );
    answers = progress.reduce((n, p) => n + (p?.completed ?? 0) + (p?.in_progress ?? 0), 0);
  } catch {
    answers = null;
  }
  return { chapter, words, answers };
}

export function ConfirmChapterDelete({
  pending,
  open,
  onCancel,
  onConfirm,
}: {
  // Kept after closing, so the text stays while the dialog animates out.
  pending: PendingDelete | null;
  open: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const answers = pending?.answers == null ? 'any answers to its questions' : plural(pending.answers, 'answer');
  return (
    <AlertDialog open={open} onOpenChange={(open) => !open && onCancel()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete &ldquo;{pending?.chapter.title}&rdquo;?</AlertDialogTitle>
          <AlertDialogDescription>
            Saving the table of contents will permanently delete {plural(pending?.words ?? 0, 'word')} and {answers}
            {pending?.chapter.children.length ? ', including its subchapters' : ''}. This cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>Delete chapter</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

/** The saved chapters this save will remove, shown beside the Save button. */
export function RemovedOnSave({ stored, toc }: { stored: Map<string, string>; toc: ChapterNode[] }) {
  const kept = new Set(toc.flatMap(withSubchapters).map((c) => c.id));
  const removed = [...stored].filter(([id]) => !kept.has(id)).map(([, title]) => title);
  // Always mounted, so a screen reader is already watching when the text appears.
  return (
    <p role="status" className="text-sm text-red-700 dark:text-red-400">
      {removed.length > 0 && `Saving will remove: ${removed.join(', ')}. Their writing and answers are deleted with them.`}
    </p>
  );
}
