/**
 * #1139: three edge cases left by the ChapterEditor split (#875), on the REAL
 * TipTap editor (jest.setup.ts mocks it globally). Only bookClient is stubbed.
 */

import { act, render, screen, waitFor } from '@testing-library/react';
import type { Editor } from '@tiptap/react';
import { ChapterEditor } from '../ChapterEditor';
import bookClient from '@/lib/api/bookClient';

jest.unmock('@tiptap/react');
jest.unmock('@tiptap/starter-kit');
jest.unmock('@tiptap/extension-placeholder');
jest.unmock('@tiptap/extension-character-count');

jest.mock('@/lib/api/bookClient');
jest.mock('../questions/QuestionContainer', () => ({ __esModule: true, default: () => null }));
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

describe('ChapterEditor edge cases (#1139)', () => {
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

  it('drops a backup that holds the same text as the server on load', async () => {
    localStorage.setItem(
      'chapter-backup-bk-A',
      JSON.stringify({ content: '<p>Alpha</p>', timestamp: Date.now() - 60_000 }),
    );
    mockBookClient.getChapterContent.mockResolvedValue(content('<p>Alpha</p>'));
    const view = render(<ChapterEditor bookId="bk" chapterId="A" />);
    await waitFor(() => expect(editorIn(view.container).getHTML()).toBe('<p>Alpha</p>'));

    expect(screen.queryByRole('button', { name: /restore backup/i })).not.toBeInTheDocument();
    expect(localStorage.getItem('chapter-backup-bk-A')).toBeNull();
  });

  it('does not fire the autosave timer after a pagehide flush', async () => {
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
    expect(mockBookClient.saveChapterContent).toHaveBeenCalledTimes(1);

    await flushTimers(5000);

    expect(mockBookClient.saveChapterContent).toHaveBeenCalledTimes(1);
  });

  it('clears the spinner when initialContent arrives while a load is in flight', async () => {
    mockBookClient.getChapterContent.mockReturnValue(new Promise(() => {}));
    const view = render(<ChapterEditor bookId="bk" chapterId="A" initialContent="" />);
    expect(screen.getByText('Loading chapter content...')).toBeInTheDocument();

    view.rerender(<ChapterEditor bookId="bk" chapterId="A" initialContent="<p>Handed</p>" />);

    await waitFor(() => expect(screen.queryByText('Loading chapter content...')).not.toBeInTheDocument());
  });
});
