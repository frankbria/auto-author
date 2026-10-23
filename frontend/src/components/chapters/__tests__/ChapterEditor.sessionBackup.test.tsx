/**
 * #1195: after a failed save, the backup holds the text the editor still shows,
 * so the Restore banner must not offer it back. A backup from an earlier load
 * that differs from the server's copy is still offered.
 *
 * Runs the REAL TipTap editor; only bookClient is stubbed.
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
const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;
type ChapterContent = Awaited<ReturnType<typeof bookClient.getChapterContent>>;

const KEY = 'chapter-backup-bk-A';
const BANNER = /local backup of your content is available/i;

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

describe('ChapterEditor: the restore banner after a failed save in this session (#1195)', () => {
  it('is not shown after a failed autosave, and the error says the text is backed up', async () => {
    mockBookClient.saveChapterContent.mockRejectedValue(new Error('Failed to save chapter content: 503'));
    const view = await open();
    view.type(' one');
    await flushTimers(3000);

    expect(JSON.parse(localStorage.getItem(KEY) ?? 'null')?.content).toBe('<p>Alpha one</p>');
    expect(view.getByText(/backed up locally/i)).toBeInTheDocument();
    expect(screen.queryByText(BANNER)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /restore backup/i })).not.toBeInTheDocument();
  });

  it('is not shown after a save refused as too large', async () => {
    mockBookClient.saveChapterContent.mockRejectedValue(Object.assign(new Error('Too long.'), { statusCode: 413 }));
    const view = await open();
    view.type(' one');
    await flushTimers(3000);

    expect(view.getByText(/Too long\./)).toBeInTheDocument();
    expect(screen.queryByText(BANNER)).not.toBeInTheDocument();
  });

  it('is not shown after a failed manual save, and the error says the text is backed up', async () => {
    mockBookClient.saveChapterContent.mockRejectedValue(new Error('Failed to save chapter content: 500'));
    const view = await open();
    view.type(' one');
    fireEvent.click(view.getByRole('button', { name: /^save/i }));
    await flushTimers(0);

    expect(view.getByText(/backed up locally/i)).toBeInTheDocument();
    expect(screen.queryByText(BANNER)).not.toBeInTheDocument();
  });

  it('is shown on load when the backup holds text the server does not', async () => {
    localStorage.setItem(KEY, JSON.stringify({ content: '<p>Alpha from before</p>', timestamp: Date.now() }));
    await open();

    expect(screen.getByText(BANNER)).toBeInTheDocument();
  });
});
