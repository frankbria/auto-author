/**
 * #758: a background TOC refresh must not unmount the chapter editor.
 *
 * `tocUpdated` (this tab) and the `toc-updated-<book>` storage event (another
 * tab) both call refreshChapters. It used to raise is_loading, so ChapterTabs
 * swapped the whole tab area for its skeleton: the editor unmounted, the user's
 * cursor and undo history went with it, and the remount fetched the chapter
 * content again.
 *
 * Runs the real ChapterTabs, useChapterTabs, useTocSync and TipTap editor; only
 * bookClient is stubbed, at its method boundary, so each test controls when the
 * refresh's TOC request resolves.
 */

import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { Editor } from '@tiptap/react';
import { ChapterTabs } from '../ChapterTabs';
import { triggerTocUpdateEvent } from '@/hooks/useTocSync';
import bookClient from '@/lib/api/bookClient';

jest.unmock('@tiptap/react');
jest.unmock('@tiptap/starter-kit');
jest.unmock('@tiptap/extension-underline');
jest.unmock('@tiptap/extension-placeholder');
jest.unmock('@tiptap/extension-character-count');

jest.mock('@/lib/api/bookClient');
const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;

type Toc = Awaited<ReturnType<typeof bookClient.getToc>>;
const toc = (...ids: string[]): Toc =>
  ({
    toc: {
      chapters: ids.map((id, i) => ({ id, title: `Chapter ${id}`, description: '', level: 1, order: i + 1, subchapters: [] })),
      total_chapters: ids.length,
      estimated_pages: 1,
      structure_notes: '',
    },
  }) as unknown as Toc;

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

// TipTap stores its instance on the ProseMirror DOM node ("for tests").
function editorNode(): HTMLElement & { editor?: Editor } {
  const dom = document.querySelector('.ProseMirror') as (HTMLElement & { editor?: Editor }) | null;
  if (!dom?.editor) throw new Error('editor not mounted');
  return dom;
}

// Compared before/after a refresh, not to a literal: a mount can request the
// content more than once (the first request runs before TipTap's instance exists).
const contentLoads = (chapterId: string) =>
  mockBookClient.getChapterContent.mock.calls.filter(([, id]) => id === chapterId).length;

async function renderWithTypedText() {
  render(<ChapterTabs bookId="bk" />);
  await waitFor(() => expect(document.querySelector('.ProseMirror')).not.toBeNull());
  const node = editorNode();
  act(() => {
    node.editor!.commands.insertContent(' typed');
  });
  return node;
}

describe('ChapterTabs background TOC refresh (#758)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    mockBookClient.getToc.mockResolvedValue(toc('A', 'B'));
    mockBookClient.getTabState.mockResolvedValue(null as never);
    mockBookClient.saveTabState.mockResolvedValue({} as never);
    mockBookClient.saveChapterContent.mockResolvedValue({} as never);
    mockBookClient.getChapterContent.mockImplementation(async (_book, id) => ({
      content: `<p>Body ${id}</p>`,
      chapter_id: id,
      book_id: 'bk',
    }));
  });

  it('keeps the same editor, its text and no extra content load across a TOC update event', async () => {
    const node = await renderWithTypedText();
    const loadsBefore = contentLoads('A');
    const refresh = deferred<Toc>();
    mockBookClient.getToc.mockReturnValueOnce(refresh.promise);

    act(() => triggerTocUpdateEvent('bk'));

    // While the refresh is in flight the editor stays, not the skeleton.
    expect(screen.queryByTestId('chapter-tabs-skeleton')).toBeNull();
    expect(document.querySelector('.ProseMirror')).toBe(node);

    await act(async () => refresh.resolve(toc('A', 'B', 'C')));

    expect(await screen.findByText('Chapter C')).toBeInTheDocument();
    expect(document.querySelector('.ProseMirror')).toBe(node);
    expect(node.editor!.getHTML()).toBe('<p>Body A typed</p>');
    expect(contentLoads('A')).toBe(loadsBefore);
  });

  it('keeps the editor through a TOC update from another tab', async () => {
    const node = await renderWithTypedText();
    const loadsBefore = contentLoads('A');
    const refresh = deferred<Toc>();
    mockBookClient.getToc.mockReturnValueOnce(refresh.promise);

    act(() => {
      window.dispatchEvent(new StorageEvent('storage', { key: 'toc-updated-bk', newValue: '1' }));
    });
    expect(screen.queryByTestId('chapter-tabs-skeleton')).toBeNull();

    await act(async () => refresh.resolve(toc('A', 'B')));

    expect(mockBookClient.getToc).toHaveBeenCalledTimes(2);
    expect(document.querySelector('.ProseMirror')).toBe(node);
    expect(contentLoads('A')).toBe(loadsBefore);
  });

  it('does not switch back to the old chapter when the user changed tabs mid-refresh', async () => {
    await renderWithTypedText();
    const refresh = deferred<Toc>();
    mockBookClient.getToc.mockReturnValueOnce(refresh.promise);

    act(() => triggerTocUpdateEvent('bk'));
    fireEvent.click(screen.getByText('Chapter B'));
    await waitFor(() => expect(editorNode().editor!.getHTML()).toBe('<p>Body B</p>'));
    const nodeB = editorNode();
    const loadsBefore = contentLoads('B');

    await act(async () => refresh.resolve(toc('A', 'B')));

    expect(document.querySelector('.ProseMirror')).toBe(nodeB);
    expect(contentLoads('B')).toBe(loadsBefore);
  });

  it('keeps the editor when a background refresh fails', async () => {
    const node = await renderWithTypedText();
    mockBookClient.getToc.mockRejectedValueOnce(new Error('toc down'));
    mockBookClient.getChaptersMetadata.mockRejectedValueOnce(new Error('metadata down'));

    await act(async () => triggerTocUpdateEvent('bk'));
    await waitFor(() => expect(mockBookClient.getChaptersMetadata).toHaveBeenCalled());

    expect(screen.queryByText('Error loading chapters')).toBeNull();
    expect(document.querySelector('.ProseMirror')).toBe(node);
    expect(node.editor!.getHTML()).toBe('<p>Body A typed</p>');
  });

  it('shows the error and its Retry only when no chapters are loaded', async () => {
    mockBookClient.getToc.mockRejectedValue(new Error('toc down'));
    mockBookClient.getChaptersMetadata.mockRejectedValue(new Error('metadata down'));
    render(<ChapterTabs bookId="bk" />);
    expect(await screen.findByTestId('empty-chapters-state')).toBeInTheDocument();

    await act(async () => triggerTocUpdateEvent('bk'));
    expect(await screen.findByText('Error loading chapters')).toBeInTheDocument();

    mockBookClient.getToc.mockResolvedValue(toc('A'));
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));

    await waitFor(() => expect(document.querySelector('.ProseMirror')).not.toBeNull());
    expect(screen.queryByText('Error loading chapters')).toBeNull();
  });
});
