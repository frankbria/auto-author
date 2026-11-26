/**
 * #1091: signing out removes the user's writing from this browser, so the next
 * person at a shared device cannot read it. An edit still waiting to save is
 * saved first; text that could not be saved is only discarded after the user
 * says so. A session that ends on its own (a 401) keeps every backup, since a
 * backup may be the only copy.
 *
 * Runs the REAL TipTap editor; only bookClient and the auth client are stubbed.
 */

import { act, render, waitFor } from '@testing-library/react';
import type { Editor } from '@tiptap/react';
import { ChapterEditor } from '../ChapterEditor';
import bookClient from '@/lib/api/bookClient';
import { authClient } from '@/lib/auth-client';
import { endSignOut, signOutOrNotify, UNSAVED_WRITING_WARNING } from '@/lib/sign-out';
import { apiFetch, browser, resetUnauthorizedForTests } from '@/lib/api/unauthorized';

jest.unmock('@tiptap/react');
jest.unmock('@tiptap/starter-kit');
jest.unmock('@tiptap/extension-placeholder');
jest.unmock('@tiptap/extension-character-count');

jest.mock('@/lib/api/bookClient');
jest.mock('@/lib/toast', () => ({ toast: jest.fn() }));
const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;
const mockSignOut = authClient.signOut as jest.Mock;
type ChapterContent = Awaited<ReturnType<typeof bookClient.getChapterContent>>;
type SaveResult = Awaited<ReturnType<typeof bookClient.saveChapterContent>>;

const KEY = 'chapter-backup-bk-A';
const SERVER_DOWN = new Error('Failed to save chapter content: 503');

function editorIn(container: HTMLElement): Editor {
  const dom = container.querySelector('.ProseMirror') as (HTMLElement & { editor?: Editor }) | null;
  if (!dom?.editor) throw new Error('editor not mounted');
  return dom.editor;
}

/** A book page with an edit typed and still inside the autosave delay. */
async function openWithUnsavedEdit() {
  const view = render(<ChapterEditor bookId="bk" chapterId="A" />);
  await waitFor(() => expect(editorIn(view.container).getHTML()).toBe('<p>Alpha</p>'));
  act(() => {
    editorIn(view.container).commands.insertContent(' one');
  });
  return view;
}

/** What user-button.tsx does: sign out, then leave the page (which unmounts the editor). */
async function signOutAndLeave(view: ReturnType<typeof render>) {
  let signedOut = false;
  await act(async () => {
    signedOut = await signOutOrNotify();
  });
  if (signedOut) view.unmount();
  // The unmount flush saves with no session; let it fail.
  await act(async () => {
    await jest.advanceTimersByTimeAsync(0);
  });
  return signedOut;
}

let confirmSpy: jest.SpyInstance;

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  sessionStorage.clear();
  endSignOut();
  resetUnauthorizedForTests();
  jest.useFakeTimers();
  jest.spyOn(console, 'error').mockImplementation(() => {});
  confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
  mockSignOut.mockResolvedValue({ data: {}, error: null });
  mockBookClient.getChapterContent.mockResolvedValue({
    content: '<p>Alpha</p>',
    chapter_id: 'A',
    book_id: 'bk',
    last_modified: 'T1',
  } as ChapterContent);
  // Another book's backup and tabs, from earlier: also this user's writing.
  localStorage.setItem('tabState_other', '{"open":["X"]}');
  localStorage.setItem('book-summary-other', 'A summary the server has');
});

afterEach(() => {
  confirmSpy.mockRestore();
  jest.useRealTimers();
});

describe('ChapterEditor: signing out from a book page (#1091)', () => {
  it('saves the unsaved edit first, then signs out without asking and leaves no writing behind', async () => {
    mockBookClient.saveChapterContent.mockResolvedValue({ last_modified: 'T2' } as SaveResult);
    const view = await openWithUnsavedEdit();

    expect(await signOutAndLeave(view)).toBe(true);

    expect(mockBookClient.saveChapterContent).toHaveBeenCalledWith(
      'bk', 'A', '<p>Alpha one</p>', true, expect.objectContaining({ expectedLastModified: 'T1' })
    );
    // Saved while the session was still alive: the save comes before the sign-out.
    expect(mockBookClient.saveChapterContent.mock.invocationCallOrder[0]).toBeLessThan(
      mockSignOut.mock.invocationCallOrder[0]
    );
    expect(confirmSpy).not.toHaveBeenCalled();
    expect(localStorage.getItem(KEY)).toBeNull();
    expect(localStorage.getItem('tabState_other')).toBeNull();
    expect(localStorage.getItem('book-summary-other')).toBeNull();
  });

  it('asks before discarding an edit that could not be saved, and on yes leaves no backup', async () => {
    mockBookClient.saveChapterContent.mockRejectedValue(SERVER_DOWN);
    const view = await openWithUnsavedEdit();

    expect(await signOutAndLeave(view)).toBe(true);

    expect(confirmSpy).toHaveBeenCalledWith(UNSAVED_WRITING_WARNING);
    expect(mockSignOut).toHaveBeenCalledTimes(1);
    // Leaving the page sends no save without a session, and writes nothing.
    expect(mockBookClient.saveChapterContent).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem(KEY)).toBeNull();
  });

  it('a save in flight when the user signs out is waited for, and nothing is written back later', async () => {
    const view = await openWithUnsavedEdit();
    // The autosave goes out and hangs; no newer edit follows it.
    let failSave: (err: Error) => void = () => {};
    mockBookClient.saveChapterContent.mockImplementation(
      () => new Promise((_resolve, reject) => (failSave = reject)) as never
    );
    await act(async () => {
      await jest.advanceTimersByTimeAsync(3000);
    });
    expect(mockBookClient.saveChapterContent).toHaveBeenCalledTimes(1);

    let signedOut: Promise<boolean> = Promise.resolve(false);
    await act(async () => {
      signedOut = signOutOrNotify();
    });
    expect(mockSignOut).not.toHaveBeenCalled();
    mockBookClient.saveChapterContent.mockRejectedValue(SERVER_DOWN);
    await act(async () => {
      failSave(SERVER_DOWN);
      await jest.advanceTimersByTimeAsync(0);
    });
    expect(await signedOut).toBe(true);
    expect(confirmSpy).toHaveBeenCalledWith(UNSAVED_WRITING_WARNING);
    view.unmount();
    // Well past the few seconds the sign-out holds the redirect guards.
    await act(async () => {
      await jest.advanceTimersByTimeAsync(60_000);
    });

    expect(localStorage.getItem(KEY)).toBeNull();
  });

  it('on no, stays signed in and keeps the backup', async () => {
    mockBookClient.saveChapterContent.mockRejectedValue(SERVER_DOWN);
    confirmSpy.mockReturnValue(false);
    const view = await openWithUnsavedEdit();

    expect(await signOutAndLeave(view)).toBe(false);

    expect(mockSignOut).not.toHaveBeenCalled();
    expect(JSON.parse(localStorage.getItem(KEY) ?? 'null')?.content).toBe('<p>Alpha one</p>');
    expect(localStorage.getItem('tabState_other')).not.toBeNull();
    view.unmount();
  });

  it('also saves an edit typed while the first save runs, before signing out', async () => {
    const view = await openWithUnsavedEdit();
    let finishFirst: (value: SaveResult) => void = () => {};
    mockBookClient.saveChapterContent
      .mockImplementationOnce(() => new Promise((resolve) => (finishFirst = resolve)))
      .mockResolvedValue({ last_modified: 'T3' } as SaveResult);

    let signedOut: Promise<boolean> = Promise.resolve(false);
    await act(async () => {
      signedOut = signOutOrNotify();
    });
    act(() => {
      editorIn(view.container).commands.insertContent(' two');
    });
    await act(async () => {
      finishFirst({ last_modified: 'T2' } as SaveResult);
      await jest.advanceTimersByTimeAsync(0);
    });

    expect(await signedOut).toBe(true);
    expect(mockBookClient.saveChapterContent).toHaveBeenLastCalledWith(
      'bk', 'A', '<p>Alpha one two</p>', true, expect.objectContaining({ expectedLastModified: 'T2' })
    );
    expect(mockBookClient.saveChapterContent.mock.invocationCallOrder[1]).toBeLessThan(
      mockSignOut.mock.invocationCallOrder[0]
    );
    expect(confirmSpy).not.toHaveBeenCalled();
    view.unmount();
  });

  it('asks about an edit that could not be saved even when the browser could not keep a copy', async () => {
    mockBookClient.saveChapterContent.mockRejectedValue(SERVER_DOWN);
    const view = await openWithUnsavedEdit();
    const setItem = jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('Quota exceeded', 'QuotaExceededError');
    });
    confirmSpy.mockReturnValue(false);

    expect(await signOutAndLeave(view)).toBe(false);

    setItem.mockRestore();
    expect(localStorage.getItem(KEY)).toBeNull();
    expect(confirmSpy).toHaveBeenCalledWith(UNSAVED_WRITING_WARNING);
    expect(mockSignOut).not.toHaveBeenCalled();
    view.unmount();
  });

  it('a sign-out that fails clears nothing', async () => {
    mockBookClient.saveChapterContent.mockRejectedValue(SERVER_DOWN);
    mockSignOut.mockResolvedValue({ data: null, error: { message: 'nope' } });
    const view = await openWithUnsavedEdit();

    expect(await signOutAndLeave(view)).toBe(false);

    expect(JSON.parse(localStorage.getItem(KEY) ?? 'null')?.content).toBe('<p>Alpha one</p>');
    expect(localStorage.getItem('tabState_other')).not.toBeNull();
    view.unmount();
  });
});

describe('ChapterEditor: a session that ends on its own (the 401 path) keeps the backup (#1091)', () => {
  const realFetch = global.fetch;
  afterEach(() => {
    global.fetch = realFetch;
  });

  it('keeps the unsaved edit as a backup when the backend answers 401', async () => {
    const go = jest.spyOn(browser, 'go').mockImplementation(() => {});
    mockBookClient.saveChapterContent.mockRejectedValue(
      Object.assign(new Error('Failed to save chapter content: 401'), { statusCode: 401 })
    );
    const view = await openWithUnsavedEdit();
    global.fetch = jest.fn().mockResolvedValue({ status: 401, ok: false } as Response);

    await act(async () => {
      await apiFetch('http://api/books');
      await jest.advanceTimersByTimeAsync(0);
    });
    expect(mockSignOut).toHaveBeenCalledTimes(1);
    expect(go).toHaveBeenCalled();
    // The page goes away; the editor's leaving flush fails without a session.
    view.unmount();
    await act(async () => {
      await jest.advanceTimersByTimeAsync(0);
    });

    expect(confirmSpy).not.toHaveBeenCalled();
    expect(JSON.parse(localStorage.getItem(KEY) ?? 'null')?.content).toBe('<p>Alpha one</p>');
    expect(localStorage.getItem('tabState_other')).not.toBeNull();
    go.mockRestore();
  });
});
