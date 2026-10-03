/**
 * #760: every save sends the chapter's save token, and a save rejected because
 * the chapter changed elsewhere keeps the writer's text and asks which to keep.
 *
 * Runs the REAL TipTap editor, like ChapterEditor.chapterSwitch.test.tsx. Only
 * bookClient is stubbed, at its method boundary; a 409 is the error shape
 * bookClient.saveChapterContent throws for the backend's conflict detail (#759).
 */

import { act, render, waitFor } from '@testing-library/react';
import type { Editor } from '@tiptap/react';
import { ChapterEditor } from '../ChapterEditor';
import bookClient from '@/lib/api/bookClient';

jest.unmock('@tiptap/react');
jest.unmock('@tiptap/starter-kit');
jest.unmock('@tiptap/extension-underline');
jest.unmock('@tiptap/extension-placeholder');
jest.unmock('@tiptap/extension-character-count');

jest.mock('@/lib/api/bookClient');
const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;

type ChapterContent = Awaited<ReturnType<typeof bookClient.getChapterContent>>;
type SaveResult = Awaited<ReturnType<typeof bookClient.saveChapterContent>>;

const BACKUP_KEY = 'chapter-backup-bk-A';

function serveChapter(content: string, last_modified: string | null) {
  mockBookClient.getChapterContent.mockResolvedValue({
    content,
    chapter_id: 'A',
    book_id: 'bk',
    last_modified,
  } as ChapterContent);
}

const saved = (last_modified: string) => ({ last_modified }) as SaveResult;

const conflict = (currentContent: string, currentLastModified: string | null) =>
  Object.assign(new Error('This chapter was saved from somewhere else since you opened it.'), {
    statusCode: 409,
    currentContent,
    currentLastModified,
  });

const saveCalls = () => mockBookClient.saveChapterContent.mock.calls;
const sentContent = () => saveCalls().map(([, , content]) => content);
const sentTokens = () => saveCalls().map((call) => call[4]?.expectedLastModified);
const backup = () => JSON.parse(localStorage.getItem(BACKUP_KEY) ?? 'null')?.content;
// Text dropped on Reload is kept apart, so a later failed save cannot overwrite it.
const dropped = () => JSON.parse(localStorage.getItem('chapter-dropped-bk-A') ?? 'null')?.content;

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
  return { ...view, type, html: () => editorIn(view.container).getHTML() };
}

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  sessionStorage.clear();
  jest.useFakeTimers();
  serveChapter('<p>Alpha</p>', 'T1');
});

afterEach(() => {
  jest.useRealTimers();
});

describe('ChapterEditor save token (#760)', () => {
  it('autosave sends the token from GET content, then the token its own save returned', async () => {
    mockBookClient.saveChapterContent.mockResolvedValueOnce(saved('T2')).mockResolvedValueOnce(saved('T3'));
    const view = await open();

    view.type(' one');
    await flushTimers(3000);
    view.type(' two');
    await flushTimers(3000);

    expect(sentContent()).toEqual(['<p>Alpha one</p>', '<p>Alpha one two</p>']);
    expect(sentTokens()).toEqual(['T1', 'T2']);
  });

  it('sends null, not nothing, for a chapter that was never saved', async () => {
    serveChapter('<p>Alpha</p>', null);
    mockBookClient.saveChapterContent.mockResolvedValue(saved('T2'));
    const view = await open();

    view.type(' one');
    await flushTimers(3000);

    expect(saveCalls()[0][4]).toHaveProperty('expectedLastModified', null);
  });

  it('manual Save sends the token', async () => {
    mockBookClient.saveChapterContent.mockResolvedValue(saved('T2'));
    const view = await open();

    view.type(' one');
    await act(async () => view.getByRole('button', { name: 'Save' }).click());

    expect(sentTokens()).toEqual(['T1']);
  });

  it('the flush on leaving sends the token with keepalive', async () => {
    mockBookClient.saveChapterContent.mockResolvedValue(saved('T2'));
    const view = await open();

    view.type(' one');
    view.unmount();
    await flushTimers(0);

    expect(saveCalls()).toEqual([
      ['bk', 'A', '<p>Alpha one</p>', true, { keepalive: true, expectedLastModified: 'T1' }],
    ]);
  });

  it('the flush after an in-flight save sends the token that save returned', async () => {
    let finishFirstSave!: () => void;
    mockBookClient.saveChapterContent
      .mockImplementationOnce(() => new Promise((resolve) => (finishFirstSave = () => resolve(saved('T2')))))
      .mockResolvedValueOnce(saved('T3'));
    const view = await open();

    view.type(' one');
    await flushTimers(3000);
    view.type(' two');
    view.unmount();
    await act(async () => finishFirstSave());
    await flushTimers(0);

    expect(sentTokens()).toEqual(['T1', 'T2']);
    expect(localStorage.getItem(BACKUP_KEY)).toBeNull();
  });
});

describe('ChapterEditor save conflict (#760)', () => {
  async function openIntoConflict() {
    mockBookClient.saveChapterContent.mockRejectedValueOnce(conflict('<p>Theirs</p>', 'T9'));
    const view = await open();
    view.type(' mine');
    await flushTimers(3000);
    return view;
  }

  it('keeps the local text, backs it up, and asks which version to keep', async () => {
    const view = await openIntoConflict();

    expect(view.getByRole('alert')).toHaveTextContent(/changed somewhere else/i);
    expect(view.getByRole('button', { name: 'Reload their version' })).toBeInTheDocument();
    expect(view.getByRole('button', { name: 'Overwrite with mine' })).toBeInTheDocument();
    expect(view.html()).toBe('<p>Alpha mine</p>');
    expect(backup()).toBe('<p>Alpha mine</p>');
    expect(view.getByTestId('save-status-indicator')).toHaveAttribute('data-save-status', 'error');
    // The backup is part of the conflict, not a separate restore offer.
    expect(view.queryByRole('button', { name: 'Restore Backup' })).toBeNull();
  });

  it('stops saving until the writer chooses: no autosave, no manual Save, no automatic overwrite', async () => {
    const view = await openIntoConflict();

    view.type(' more');
    await flushTimers(10000);

    expect(view.getByRole('button', { name: 'Save' })).toBeDisabled();
    expect(saveCalls()).toHaveLength(1);
  });

  it('Overwrite resends the current text on the server copy token, once', async () => {
    const view = await openIntoConflict();
    mockBookClient.saveChapterContent.mockResolvedValueOnce(saved('T10')).mockResolvedValueOnce(saved('T11'));
    view.type(' more');

    await act(async () => view.getByRole('button', { name: 'Overwrite with mine' }).click());

    expect(sentContent()[1]).toBe('<p>Alpha mine more</p>');
    expect(sentTokens()[1]).toBe('T9');
    expect(view.queryByRole('alert')).toBeNull();
    expect(localStorage.getItem(BACKUP_KEY)).toBeNull();

    // Autosave resumes on the overwrite's own token.
    view.type(' after');
    await flushTimers(3000);
    expect(sentTokens()).toEqual(['T1', 'T9', 'T10']);
  });

  it('Reload shows the server copy, keeps the local text as a backup, and saves nothing', async () => {
    const view = await openIntoConflict();
    view.type(' more');

    await act(async () => view.getByRole('button', { name: 'Reload their version' }).click());
    await flushTimers(10000);

    expect(view.html()).toBe('<p>Theirs</p>');
    expect(dropped()).toBe('<p>Alpha mine more</p>');
    expect(saveCalls()).toHaveLength(1);
    expect(view.queryByRole('button', { name: 'Overwrite with mine' })).toBeNull();
    expect(view.getByRole('button', { name: 'Restore Backup' })).toBeInTheDocument();
  });

  it('after Reload, edits and a restored backup save on the server copy token', async () => {
    const view = await openIntoConflict();
    await act(async () => view.getByRole('button', { name: 'Reload their version' }).click());
    mockBookClient.saveChapterContent.mockResolvedValue(saved('T10'));

    await act(async () => view.getByRole('button', { name: 'Restore Backup' }).click());
    await flushTimers(3000);

    expect(sentContent()[1]).toBe('<p>Alpha mine</p>');
    expect(sentTokens()[1]).toBe('T9');
  });

  it('keeps the text dropped on Reload restorable after later saves and leaving', async () => {
    const view = await openIntoConflict();
    await act(async () => view.getByRole('button', { name: 'Reload their version' }).click());
    mockBookClient.saveChapterContent.mockResolvedValue(saved('T10'));

    view.type(' edit');
    await flushTimers(3000);
    view.type(' again');
    view.unmount();
    await flushTimers(0);

    expect(sentContent().slice(1)).toEqual(['<p>Theirs edit</p>', '<p>Theirs edit again</p>']);
    expect(dropped()).toBe('<p>Alpha mine</p>');
  });

  it('keeps the text dropped on Reload restorable when a later save fails and is backed up', async () => {
    const view = await openIntoConflict();
    view.type(' more');
    await act(async () => view.getByRole('button', { name: 'Reload their version' }).click());
    mockBookClient.saveChapterContent.mockRejectedValue(new Error('offline'));

    view.type(' edit');
    await flushTimers(3000);
    expect(backup()).toBe('<p>Theirs edit</p>');

    // Both versions stay on offer: dismissing the failed save's backup leaves the dropped text.
    await act(async () => view.getByRole('button', { name: 'Dismiss' }).click());
    await act(async () => view.getByRole('button', { name: 'Restore Backup' }).click());
    expect(view.html()).toBe('<p>Alpha mine more</p>');
  });

  it('does not claim a backup when the conflict text could not be stored', async () => {
    mockBookClient.saveChapterContent.mockRejectedValueOnce(conflict('<p>Theirs</p>', 'T9'));
    const view = await open();
    view.type(' mine');
    const setItem = jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('Storage full', 'QuotaExceededError');
    });
    await flushTimers(3000);
    setItem.mockRestore();

    expect(view.getByRole('alert')).toHaveTextContent(/could not be backed up/i);
    expect(view.getByRole('alert')).not.toHaveTextContent(/backed up on this device\. Which/i);
    expect(view.html()).toBe('<p>Alpha mine</p>');
  });

  it('keeps the text in the editor when Reload cannot back it up', async () => {
    const view = await openIntoConflict();
    view.type(' more');
    const setItem = jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('Storage full', 'QuotaExceededError');
    });

    await act(async () => view.getByRole('button', { name: 'Reload their version' }).click());
    setItem.mockRestore();

    expect(view.html()).toBe('<p>Alpha mine more</p>');
    expect(view.getByRole('alert')).toHaveTextContent(/could not back up/i);
    expect(view.getByRole('button', { name: 'Overwrite with mine' })).toBeInTheDocument();

    // Still the editor's unsaved edit: leaving tries to save it.
    mockBookClient.saveChapterContent.mockRejectedValue(conflict('<p>Theirs</p>', 'T9'));
    view.unmount();
    await flushTimers(0);
    expect(sentContent().at(-1)).toBe('<p>Alpha mine more</p>');
  });

  it('does not raise a conflict on the next chapter for a save that 409s after a swap', async () => {
    let rejectHeld!: () => void;
    mockBookClient.saveChapterContent
      .mockImplementationOnce(
        () => new Promise((_, reject) => (rejectHeld = () => reject(conflict('<p>Theirs</p>', 'T9'))))
      )
      .mockRejectedValue(conflict('<p>Theirs</p>', 'T9'));
    const view = await open();
    view.type(' mine');
    await flushTimers(3000);

    view.rerender(<ChapterEditor bookId="bk" chapterId="C" />);
    await act(async () => rejectHeld());
    await flushTimers(0);

    await waitFor(() => expect(view.getByRole('button', { name: 'Save' })).toBeEnabled());
    expect(view.queryByRole('button', { name: 'Overwrite with mine' })).toBeNull();
    // Chapter A's text is still kept, under chapter A.
    expect(backup()).toBe('<p>Alpha mine</p>');
  });

  it('does not carry a conflict over to another chapter shown in the same editor', async () => {
    const view = await openIntoConflict();
    mockBookClient.saveChapterContent.mockResolvedValue(saved('T2'));

    view.rerender(<ChapterEditor bookId="bk" chapterId="C" />);
    await waitFor(() => expect(view.getByRole('button', { name: 'Save' })).toBeEnabled());

    expect(view.queryByRole('button', { name: 'Overwrite with mine' })).toBeNull();
  });

  it('backs up edits made during the conflict when the editor is left unresolved', async () => {
    const view = await openIntoConflict();
    mockBookClient.saveChapterContent.mockRejectedValue(conflict('<p>Theirs</p>', 'T9'));
    view.type(' more');

    view.unmount();
    await flushTimers(0);

    // The flush must not overwrite the other version on the writer's behalf.
    expect(sentTokens()).toEqual(['T1', 'T1']);
    expect(backup()).toBe('<p>Alpha mine more</p>');
  });

  it('treats a token bump with unchanged text (a status change) as no conflict', async () => {
    mockBookClient.saveChapterContent
      .mockRejectedValueOnce(conflict('<p>Alpha</p>', 'T5'))
      .mockResolvedValueOnce(saved('T6'));
    const view = await open();

    view.type(' mine');
    await flushTimers(3000);

    expect(sentTokens()).toEqual(['T1', 'T5']);
    expect(sentContent()).toEqual(['<p>Alpha mine</p>', '<p>Alpha mine</p>']);
    expect(view.queryByRole('alert')).toBeNull();
  });
});
