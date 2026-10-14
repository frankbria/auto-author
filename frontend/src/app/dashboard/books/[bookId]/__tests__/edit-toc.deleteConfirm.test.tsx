/**
 * Deleting a chapter on Edit TOC asks first when it holds writing or answers (#906).
 *
 * Since #755 a saved TOC without a chapter also deletes that chapter's
 * questions and answers, so a mis-click followed by Save destroyed the draft
 * and every answer behind it.
 */
import React, { Suspense } from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { useSession } from '@/lib/auth-client';
import { bookClient } from '@/lib/api/bookClient';
import EditTOCPage from '../edit-toc/page';

jest.mock('next/navigation', () => ({ useRouter: () => ({ push: jest.fn() }) }));
jest.mock('@/lib/auth-client');
jest.mock('@/lib/api/bookClient');
jest.mock('@/hooks/useTocSync', () => ({ triggerTocUpdateEvent: jest.fn() }));

const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;

function fulfilledParams<T>(value: T): Promise<T> {
  const p = Promise.resolve(value) as Promise<T> & { status: string; value: T };
  p.status = 'fulfilled';
  p.value = value;
  return p;
}

const chapter = (id: string, title: string, word_count: number, subchapters: unknown[] = []) => ({
  id, title, description: '', level: 1, order: 1, status: 'draft', word_count, subchapters,
});

const answers = (byChapter: Record<string, number>) =>
  mockBookClient.getChapterQuestionProgress.mockImplementation(async (_b, chapterId) => {
    const n = byChapter[chapterId] ?? 0;
    return { total: n, completed: n - Math.min(n, 1), in_progress: Math.min(n, 1), progress: 0, status: 'in-progress' } as never;
  });

function renderPage(chapters: unknown[]) {
  mockBookClient.getToc.mockResolvedValue({
    toc: { chapters, total_chapters: chapters.length, estimated_pages: 1, structure_notes: '' },
    version: 3,
  } as never);
  render(
    <Suspense fallback={null}>
      <EditTOCPage params={fulfilledParams({ bookId: 'book-1' })} />
    </Suspense>
  );
}

const deleteButtonOf = (title: string) =>
  screen.getByDisplayValue(title).closest('[data-chapter-row]')!.querySelector('button[title="Delete Chapter"]')!;

beforeEach(() => {
  jest.clearAllMocks();
  (useSession as jest.Mock).mockReturnValue({ data: { user: { id: 'u1' } } });
  mockBookClient.updateToc.mockResolvedValue(undefined as never);
  answers({});
});

it('deletes a chapter with no writing and no answers without asking', async () => {
  renderPage([chapter('c1', 'Keep', 10), chapter('c2', 'Empty', 0)]);
  await screen.findByDisplayValue('Empty');
  fireEvent.click(deleteButtonOf('Empty'));

  await waitFor(() => expect(screen.queryByDisplayValue('Empty')).not.toBeInTheDocument());
  expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
});

it('asks before deleting a chapter with writing or answers, naming what is lost', async () => {
  answers({ c2: 3 });
  renderPage([chapter('c1', 'Keep', 10), chapter('c2', 'Drafted', 1250)]);
  await screen.findByDisplayValue('Drafted');
  fireEvent.click(deleteButtonOf('Drafted'));

  const dialog = await screen.findByRole('alertdialog');
  expect(dialog).toHaveTextContent('1,250 words');
  expect(dialog).toHaveTextContent('3 answers');

  fireEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }));
  await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
  expect(screen.getByDisplayValue('Drafted')).toBeInTheDocument();

  fireEvent.click(deleteButtonOf('Drafted'));
  fireEvent.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Delete chapter' }));
  await waitFor(() => expect(screen.queryByDisplayValue('Drafted')).not.toBeInTheDocument());
});

it('counts the writing and answers of the subchapters that go with it', async () => {
  answers({ s1: 2 });
  renderPage([chapter('c1', 'Parent', 0, [{ ...chapter('s1', 'Child', 40), level: 2 }])]);
  await screen.findByDisplayValue('Parent');
  fireEvent.click(deleteButtonOf('Parent'));

  const dialog = await screen.findByRole('alertdialog');
  expect(dialog).toHaveTextContent('40 words');
  expect(dialog).toHaveTextContent('2 answers');
});

it('still asks when the answers cannot be counted', async () => {
  mockBookClient.getChapterQuestionProgress.mockRejectedValue(new Error('offline'));
  renderPage([chapter('c1', 'Keep', 10), chapter('c2', 'Unknown', 0)]);
  await screen.findByDisplayValue('Unknown');
  fireEvent.click(deleteButtonOf('Unknown'));

  expect(await screen.findByRole('alertdialog')).toHaveTextContent(/answers/i);
});

it('lists the saved chapters the save will remove, but not a chapter added and removed here', async () => {
  renderPage([chapter('c1', 'Keep', 10), chapter('c2', 'Gone', 0)]);
  await screen.findByDisplayValue('Gone');
  fireEvent.click(deleteButtonOf('Gone'));
  fireEvent.click(screen.getByRole('button', { name: /add chapter/i }));
  fireEvent.click(deleteButtonOf('New Chapter'));

  const summary = await screen.findByText(/saving will remove/i);
  expect(summary).toHaveTextContent('Gone');
  expect(summary).not.toHaveTextContent('New Chapter');
});
