/**
 * #875: the save gaps left after the ChapterEditor split, on the REAL TipTap
 * editor (jest.setup.ts mocks it globally). Only bookClient is stubbed, at its
 * method boundary, and the Questions panel, which here just hands a draft over.
 */

import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { Editor } from '@tiptap/react';
import { ChapterEditor } from '../ChapterEditor';
import bookClient from '@/lib/api/bookClient';

jest.unmock('@tiptap/react');
jest.unmock('@tiptap/starter-kit');
jest.unmock('@tiptap/extension-placeholder');
jest.unmock('@tiptap/extension-character-count');

jest.mock('@/lib/api/bookClient');
jest.mock('../questions/QuestionContainer', () => ({
  __esModule: true,
  default: ({
    onDraftGenerated,
    onSwitchToEditor,
  }: {
    onDraftGenerated: (draft: string) => void;
    onSwitchToEditor: () => void;
  }) => (
    <button
      onClick={() => {
        onDraftGenerated('<p>Draft</p>');
        onSwitchToEditor();
      }}
    >
      Use This Draft
    </button>
  ),
}));
const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;

type ChapterContent = Awaited<ReturnType<typeof bookClient.getChapterContent>>;
const content = (html: string): ChapterContent => ({ content: html, chapter_id: 'A', book_id: 'bk' });

function editorIn(container: HTMLElement): Editor {
  const dom = container.querySelector('.ProseMirror') as (HTMLElement & { editor?: Editor }) | null;
  if (!dom?.editor) throw new Error('editor not mounted');
  return dom.editor;
}

const flushTimers = (ms: number) =>
  act(async () => {
    await jest.advanceTimersByTimeAsync(ms);
  });

// jsdom has no layout, and ProseMirror measures a text range when the draft
// insert focuses the editor.
Range.prototype.getClientRects = () => [] as unknown as DOMRectList;
Range.prototype.getBoundingClientRect = () => new DOMRect();

describe('ChapterEditor save gaps (#875)', () => {
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

  it('requests the chapter content once per mount (#758)', async () => {
    mockBookClient.getChapterContent.mockResolvedValue(content('<p>Alpha</p>'));
    const view = render(<ChapterEditor bookId="bk" chapterId="A" />);

    await waitFor(() => expect(editorIn(view.container).getHTML()).toBe('<p>Alpha</p>'));
    await flushTimers(5000);

    expect(mockBookClient.getChapterContent).toHaveBeenCalledTimes(1);
  });

  it('sends an edit still inside the autosave debounce with keepalive when the page is hidden', async () => {
    mockBookClient.getChapterContent.mockResolvedValue(content('<p>Alpha</p>'));
    const view = render(<ChapterEditor bookId="bk" chapterId="A" />);
    await waitFor(() => expect(editorIn(view.container).getHTML()).toBe('<p>Alpha</p>'));
    act(() => {
      editorIn(view.container).commands.insertContent(' typed');
    });

    act(() => {
      window.dispatchEvent(new Event('pagehide'));
    });
    await flushTimers(0);

    expect(mockBookClient.saveChapterContent.mock.calls).toEqual([
      ['bk', 'A', '<p>Alpha typed</p>', true, { keepalive: true }],
    ]);
  });

  it('keeps a Questions-tab draft inserted while the load had failed, and saves it after Retry', async () => {
    mockBookClient.getChapterContent.mockRejectedValue(new Error('offline'));
    sessionStorage.setItem('chapterQuestionsTab_bk_A', 'questions');
    const view = render(<ChapterEditor bookId="bk" chapterId="A" />);
    const retry = await screen.findByRole('button', { name: 'Retry' });

    fireEvent.click(screen.getByRole('button', { name: 'Use This Draft' }));
    mockBookClient.getChapterContent.mockResolvedValue(content('<p>Server</p>'));
    await act(async () => fireEvent.click(retry));
    await waitFor(() => expect(editorIn(view.container).getHTML()).toBe('<p>Server</p><p>Draft</p>'));
    await flushTimers(5000);

    expect(mockBookClient.saveChapterContent.mock.calls.map(([, , html]) => html)).toEqual([
      '<p>Server</p><p>Draft</p>',
    ]);
  });
});
