/**
 * #1038: a save the server refuses as too large (413) is final until the text
 * changes. The writer is told in the server's words, the text is backed up, and
 * autosave stops retrying the same refused content.
 *
 * Runs the REAL TipTap editor like ChapterEditor.conflict.test.tsx; only
 * bookClient is stubbed.
 */

import { act, render, waitFor } from '@testing-library/react';
import type { Editor } from '@tiptap/react';
import { ChapterEditor } from '../ChapterEditor';
import bookClient from '@/lib/api/bookClient';

jest.unmock('@tiptap/react');
jest.unmock('@tiptap/starter-kit');
jest.unmock('@tiptap/extension-placeholder');
jest.unmock('@tiptap/extension-character-count');

jest.mock('@/lib/api/bookClient');
const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;

type ChapterContent = Awaited<ReturnType<typeof bookClient.getChapterContent>>;
type SaveResult = Awaited<ReturnType<typeof bookClient.saveChapterContent>>;

const DETAIL = 'This chapter is too long to save: the limit is 500,000 bytes. Split it into two chapters.';
const tooLarge = () => Object.assign(new Error(DETAIL), { statusCode: 413 });
const backup = () => JSON.parse(localStorage.getItem('chapter-backup-bk-A') ?? 'null');

function editorIn(container: HTMLElement): Editor {
  const dom = container.querySelector('.ProseMirror') as (HTMLElement & { editor?: Editor }) | null;
  if (!dom?.editor) throw new Error('editor not mounted');
  return dom.editor;
}

const flushTimers = (ms: number) =>
  act(async () => {
    await jest.advanceTimersByTimeAsync(ms);
  });

async function open() {
  const view = render(<ChapterEditor bookId="bk" chapterId="A" />);
  await waitFor(() => expect(editorIn(view.container).getHTML()).toBe('<p>Alpha</p>'));
  const type = (text: string) =>
    act(() => {
      editorIn(view.container).commands.insertContent(text);
    });
  return { ...view, type };
}

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  jest.useFakeTimers();
  jest.spyOn(console, 'error').mockImplementation(() => {});
  mockBookClient.getChapterContent.mockResolvedValue({
    content: '<p>Alpha</p>',
    chapter_id: 'A',
    book_id: 'bk',
    last_modified: 'T1',
  } as ChapterContent);
});

afterEach(() => {
  jest.useRealTimers();
});

describe('ChapterEditor: a save refused as too large (#1038)', () => {
  it('shows the server message, backs the text up, and stops retrying until the content changes', async () => {
    mockBookClient.saveChapterContent.mockRejectedValue(tooLarge());
    const view = await open();

    view.type(' one');
    await flushTimers(3000);

    expect(view.getByText(DETAIL, { exact: false })).toBeInTheDocument();
    expect(backup()?.content).toBe('<p>Alpha one</p>');
    expect(mockBookClient.saveChapterContent).toHaveBeenCalledTimes(1);

    // Well past the 30s backoff cap: nothing more is sent for the same text.
    await flushTimers(120_000);
    expect(mockBookClient.saveChapterContent).toHaveBeenCalledTimes(1);

    // Changed content is worth one new try.
    view.type(' two');
    await flushTimers(3000);
    expect(mockBookClient.saveChapterContent).toHaveBeenCalledTimes(2);
    expect(mockBookClient.saveChapterContent.mock.calls[1][2]).toBe('<p>Alpha one two</p>');
  });

  it('a manual Save shows the server message and backs the text up', async () => {
    mockBookClient.saveChapterContent.mockRejectedValue(tooLarge());
    const view = await open();

    view.type(' one');
    await act(async () => view.getByRole('button', { name: 'Save' }).click());

    expect(view.getByText(DETAIL, { exact: false })).toBeInTheDocument();
    expect(backup()?.content).toBe('<p>Alpha one</p>');
  });

  it('saves again once the content has shrunk and changed', async () => {
    mockBookClient.saveChapterContent.mockRejectedValueOnce(tooLarge());
    mockBookClient.saveChapterContent.mockResolvedValue({ last_modified: 'T2' } as SaveResult);
    const view = await open();

    view.type(' one');
    await flushTimers(3000);
    view.type('!');
    await flushTimers(3000);

    expect(mockBookClient.saveChapterContent).toHaveBeenCalledTimes(2);
  });
});
