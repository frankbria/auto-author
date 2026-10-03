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
    expect(getByText('Loading chapter content...')).toBeInTheDocument();

    await act(async () => loadC.resolve('<p>Charlie</p>'));
    await waitFor(() => expect(container.querySelector('.ProseMirror')).not.toBeNull());
    expect(editorIn(container).getHTML()).toBe('<p>Charlie</p>');
    // C loaded fine, so B's failure must not be reported over it.
    expect(queryByRole('alert')).toBeNull();
  });

  // Keying makes every tab switch a fresh mount and load, so the first typing
  // after a load is the common path, not an edge case.
  it('autosaves typing that starts more than one debounce after the load', async () => {
    const load = deferred('A');
    mockBookClient.getChapterContent.mockReturnValue(load.promise);

    const { container } = render(<ChapterEditor bookId="bk" chapterId="A" />);
    await act(async () => load.resolve('<p>Alpha</p>'));
    await waitFor(() => expect(container.querySelector('.ProseMirror')).not.toBeNull());

    // The user reads for a while before typing.
    await act(async () => {
      await jest.advanceTimersByTimeAsync(5000);
    });
    act(() => {
      editorIn(container).commands.insertContent(' later');
    });
    await act(async () => {
      await jest.advanceTimersByTimeAsync(5000);
    });

    expect(savesTo('A').map(([, , content]) => content)).toEqual(['<p>Alpha later</p>']);
  });
});

// #757: an edit must reach the chapter it was typed into, even if the editor
// goes away first or the edit lands while a save is in flight; and a chapter
// that never loaded must never be saved over.
describe('ChapterEditor pending edits (#757)', () => {
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

  async function loadThenType(view: ReturnType<typeof render>, load: Deferred, html: string, typed: string) {
    await act(async () => load.resolve(html));
    await waitFor(() => expect(view.container.querySelector('.ProseMirror')).not.toBeNull());
    act(() => {
      editorIn(view.container).commands.insertContent(typed);
    });
  }

  const flushTimers = (ms: number) =>
    act(async () => {
      await jest.advanceTimersByTimeAsync(ms);
    });

  it('saves text typed inside the debounce to its own chapter when the tab switches', async () => {
    const loads: Record<string, Deferred> = { A: deferred('A'), B: deferred('B') };
    mockBookClient.getChapterContent.mockImplementation((_book, id) => loads[id].promise);
    const props = { bookId: 'bk', chapters: [] };
    const view = render(<TabContent {...props} activeChapterId="A" />);
    await loadThenType(view, loads.A, '<p>Alpha</p>', ' typed');

    view.rerender(<TabContent {...props} activeChapterId="B" />);
    await flushTimers(5000);

    expect(savesTo('A')).toEqual([['bk', 'A', '<p>Alpha typed</p>', true, { keepalive: true }]]);
    expect(savesTo('B')).toEqual([]);
  });

  it('saves the edit to the original chapter when a caller swaps chapterId without remounting', async () => {
    const loads: Record<string, Deferred> = { B: deferred('B'), C: deferred('C') };
    mockBookClient.getChapterContent.mockImplementation((_book, id) => loads[id].promise);
    const view = render(<ChapterEditor bookId="bk" chapterId="B" />);
    await loadThenType(view, loads.B, '<p>Bravo</p>', ' edit');

    view.rerender(<ChapterEditor bookId="bk" chapterId="C" />);
    await act(async () => loads.C.resolve('<p>Charlie</p>'));
    await flushTimers(5000);

    expect(savesTo('B').map(([, , content]) => content)).toEqual(['<p>Bravo edit</p>']);
    expect(savesTo('C')).toEqual([]);
  });

  it('backs the edit up under its own chapter when the flush fails', async () => {
    const load = deferred('A');
    mockBookClient.getChapterContent.mockReturnValue(load.promise);
    mockBookClient.saveChapterContent.mockRejectedValue(new Error('offline'));
    const view = render(<ChapterEditor bookId="bk" chapterId="A" />);
    await loadThenType(view, load, '<p>Alpha</p>', ' typed');

    view.unmount();
    await flushTimers(0);

    const backup = JSON.parse(localStorage.getItem('chapter-backup-bk-A') ?? 'null');
    expect(backup?.content).toBe('<p>Alpha typed</p>');
  });

  it('does not flush an edit the user already reverted to the saved text', async () => {
    const load = deferred('A');
    mockBookClient.getChapterContent.mockReturnValue(load.promise);
    const view = render(<ChapterEditor bookId="bk" chapterId="A" />);
    await loadThenType(view, load, '<p>Alpha</p>', ' typo');
    act(() => {
      editorIn(view.container).commands.setContent('<p>Alpha</p>');
    });

    view.unmount();
    await flushTimers(0);

    expect(mockBookClient.saveChapterContent).not.toHaveBeenCalled();
  });

  it('saves an edit typed while the previous save was in flight', async () => {
    const load = deferred('A');
    mockBookClient.getChapterContent.mockReturnValue(load.promise);
    let finishFirstSave!: () => void;
    mockBookClient.saveChapterContent.mockImplementationOnce(
      () => new Promise((resolve) => (finishFirstSave = () => resolve({} as never)))
    );
    const view = render(<ChapterEditor bookId="bk" chapterId="A" />);
    await loadThenType(view, load, '<p>Alpha</p>', ' one');

    await flushTimers(3000);
    expect(savesTo('A')).toHaveLength(1);
    act(() => {
      editorIn(view.container).commands.insertContent(' two');
    });
    await act(async () => finishFirstSave());
    await flushTimers(5000);

    expect(savesTo('A').map(([, , content]) => content)).toEqual([
      '<p>Alpha one</p>',
      '<p>Alpha one two</p>',
    ]);
  });

  it('lets an in-flight save land before the flush, and keeps a failed flush backed up', async () => {
    const load = deferred('A');
    mockBookClient.getChapterContent.mockReturnValue(load.promise);
    let finishFirstSave!: () => void;
    mockBookClient.saveChapterContent
      .mockImplementationOnce(() => new Promise((resolve) => (finishFirstSave = () => resolve({} as never))))
      .mockRejectedValueOnce(new Error('offline'));
    const view = render(<ChapterEditor bookId="bk" chapterId="A" />);
    await loadThenType(view, load, '<p>Alpha</p>', ' one');
    await flushTimers(3000);
    act(() => {
      editorIn(view.container).commands.insertContent(' two');
    });

    view.unmount();
    await flushTimers(0);
    // The older save is still out: sending the newer edit now could let it land last.
    expect(savesTo('A')).toHaveLength(1);

    // The older save succeeds (clearing any backup), then the flush fails.
    await act(async () => finishFirstSave());
    await flushTimers(0);

    expect(savesTo('A').map(([, , content]) => content)).toEqual([
      '<p>Alpha one</p>',
      '<p>Alpha one two</p>',
    ]);
    const backup = JSON.parse(localStorage.getItem('chapter-backup-bk-A') ?? 'null');
    expect(backup?.content).toBe('<p>Alpha one two</p>');
  });

  it('does not save on leaving a chapter the user never edited', async () => {
    const load = deferred('A');
    mockBookClient.getChapterContent.mockReturnValue(load.promise);
    const view = render(<ChapterEditor bookId="bk" chapterId="A" />);
    await act(async () => load.resolve('<p>Alpha</p>'));
    await waitFor(() => expect(view.container.querySelector('.ProseMirror')).not.toBeNull());

    view.unmount();
    await flushTimers(0);

    expect(mockBookClient.saveChapterContent).not.toHaveBeenCalled();
  });

  describe('when the chapter fails to load', () => {
    let serverDown: boolean;
    beforeEach(() => {
      serverDown = true;
      mockBookClient.getChapterContent.mockImplementation(async () => {
        if (serverDown) throw new Error('Failed to get chapter content: 500');
        return { content: '<p>Real chapter</p>', chapter_id: 'A', book_id: 'bk' };
      });
    });

    it('is read-only, offers no editing tools, and never saves over the chapter', async () => {
      localStorage.setItem(
        'chapter-backup-bk-A',
        JSON.stringify({ content: '<p>old backup</p>', timestamp: Date.now() })
      );
      const view = render(<ChapterEditor bookId="bk" chapterId="A" />);

      await view.findByRole('button', { name: 'Retry' });
      const editor = editorIn(view.container);
      expect(editor.isEditable).toBe(false);
      expect(view.queryByRole('toolbar')).toBeNull();
      expect(view.queryByRole('button', { name: 'Restore Backup' })).toBeNull();
      expect(view.getByRole('button', { name: 'Save' })).toBeDisabled();

      // A programmatic edit bypasses read-only; it must still never be saved,
      // neither by autosave nor by the flush on leaving.
      act(() => {
        editor.commands.setContent('<p>should never be saved</p>');
      });
      await flushTimers(5000);
      view.unmount();
      await flushTimers(0);

      expect(mockBookClient.saveChapterContent).not.toHaveBeenCalled();
    });

    it('loads the chapter, editable, when Retry succeeds', async () => {
      const view = render(<ChapterEditor bookId="bk" chapterId="A" />);
      const retry = await view.findByRole('button', { name: 'Retry' });

      serverDown = false;
      await act(async () => retry.click());

      await waitFor(() => expect(editorIn(view.container).getHTML()).toBe('<p>Real chapter</p>'));
      expect(editorIn(view.container).isEditable).toBe(true);
      expect(view.queryByRole('button', { name: 'Retry' })).toBeNull();
      expect(view.getByRole('toolbar')).toBeInTheDocument();
    });
  });
});
