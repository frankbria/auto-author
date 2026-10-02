/**
 * #756: the editor must never save one chapter's text into another.
 *
 * Runs the REAL TipTap editor (jest.setup.ts mocks it globally): the bug lives
 * in what editor.getHTML() returns after a chapter change, which a mock that
 * stores a string per instance cannot reproduce.
 *
 * Only bookClient is stubbed, at its method boundary, so each test controls
 * when a chapter's content load resolves.
 */

import { act, render, waitFor } from '@testing-library/react';
import type { Editor } from '@tiptap/react';
import { ChapterEditor } from '../ChapterEditor';
import { TabContent } from '../TabContent';
import bookClient from '@/lib/api/bookClient';

jest.unmock('@tiptap/react');
jest.unmock('@tiptap/starter-kit');
jest.unmock('@tiptap/extension-underline');
jest.unmock('@tiptap/extension-placeholder');
jest.unmock('@tiptap/extension-character-count');

jest.mock('@/lib/api/bookClient');
const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;

type ChapterContent = Awaited<ReturnType<typeof bookClient.getChapterContent>>;
type Deferred = { promise: Promise<ChapterContent>; resolve: (content: string) => void };
function deferred(chapterId: string): Deferred {
  let resolve!: (content: string) => void;
  const promise = new Promise<ChapterContent>((r) => {
    resolve = (content) => r({ content, chapter_id: chapterId, book_id: 'bk' });
  });
  return { promise, resolve };
}

// TipTap stores its instance on the ProseMirror DOM node ("for tests").
function editorIn(container: HTMLElement): Editor {
  const dom = container.querySelector('.ProseMirror') as (HTMLElement & { editor?: Editor }) | null;
  if (!dom?.editor) throw new Error('editor not mounted');
  return dom.editor;
}

const savesTo = (chapterId: string) =>
  mockBookClient.saveChapterContent.mock.calls.filter(([, id]) => id === chapterId);

describe('ChapterEditor chapter switching (#756)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    jest.useFakeTimers();
    mockBookClient.saveChapterContent.mockResolvedValue({} as never);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('does not save chapter A text into chapter B when the tab switches before autosave', async () => {
    const loads: Record<string, Deferred> = { A: deferred('A'), B: deferred('B') };
    mockBookClient.getChapterContent.mockImplementation((_book, id) => loads[id].promise);

    const props = { bookId: 'bk', chapters: [] };
    const { container, rerender } = render(<TabContent {...props} activeChapterId="A" />);

    await act(async () => loads.A.resolve('<p>Alpha</p>'));
    await waitFor(() => expect(container.querySelector('.ProseMirror')).not.toBeNull());
    act(() => {
      editorIn(container).commands.insertContent(' typed');
    });

    // Switch to B while A's autosave is still pending; B's content is slow.
    rerender(<TabContent {...props} activeChapterId="B" />);
    await act(async () => {
      await jest.advanceTimersByTimeAsync(5000);
    });

    const leaked = savesTo('B').filter(([, , content]) => content.includes('typed'));
    expect(leaked).toEqual([]);
  });

  it('ignores a late content response for a chapter that is no longer active', async () => {
    const loads: Record<string, Deferred> = { B: deferred('B'), C: deferred('C') };
    mockBookClient.getChapterContent.mockImplementation((_book, id) => loads[id].promise);

    // Rendered without a key, so one editor instance sees both chapters.
    const { container, rerender } = render(<ChapterEditor bookId="bk" chapterId="B" />);
    rerender(<ChapterEditor bookId="bk" chapterId="C" />);

    await act(async () => loads.C.resolve('<p>Charlie</p>'));
    await act(async () => loads.B.resolve('<p>Bravo</p>'));
    await waitFor(() => expect(container.querySelector('.ProseMirror')).not.toBeNull());

    const editor = editorIn(container);
    expect(editor.getHTML()).toBe('<p>Charlie</p>');

    act(() => {
      editor.commands.insertContent(' more');
    });
    await act(async () => {
      await jest.advanceTimersByTimeAsync(5000);
    });

    expect(savesTo('C').map(([, , content]) => content)).toEqual(['<p>Charlie more</p>']);
  });

  it('lets a superseded load neither raise an error nor end the current spinner', async () => {
    let rejectB!: (err: Error) => void;
    const loadB = new Promise<never>((_, reject) => {
      rejectB = reject;
    });
    const loadC = deferred('C');
    mockBookClient.getChapterContent.mockImplementation((_book, id) =>
      id === 'B' ? loadB : loadC.promise
    );

    const { container, queryByRole, getByText, rerender } = render(
      <ChapterEditor bookId="bk" chapterId="B" />
    );
    rerender(<ChapterEditor bookId="bk" chapterId="C" />);

    await act(async () => rejectB(new Error('network down')));
    expect(queryByRole('alert')).toBeNull();
    expect(getByText('Loading chapter content...')).toBeInTheDocument();

    await act(async () => loadC.resolve('<p>Charlie</p>'));
    await waitFor(() => expect(container.querySelector('.ProseMirror')).not.toBeNull());
    expect(editorIn(container).getHTML()).toBe('<p>Charlie</p>');
  });
});
