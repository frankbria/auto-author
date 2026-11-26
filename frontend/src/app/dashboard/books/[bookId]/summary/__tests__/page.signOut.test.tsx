import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import BookSummaryPage from '../page';
import bookClient from '@/lib/api/bookClient';
import { authClient } from '@/lib/auth-client';
import { endSignOut, resetLeavingSavesForTests, signOutOrNotify, UNSAVED_WRITING_WARNING } from '@/lib/sign-out';

jest.mock('@/lib/api/bookClient');
jest.mock('@/lib/toast', () => ({ toast: jest.fn() }));
jest.mock('@/lib/voice/useSpeechRecognitionSupported', () => ({
  useSpeechRecognitionSupported: () => false,
}));
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
  useParams: () => ({ bookId: 'book-1' }),
}));

const mockedClient = bookClient as jest.Mocked<typeof bookClient>;
const mockSignOut = authClient.signOut as jest.Mock;
type SummaryResponse = Awaited<ReturnType<typeof bookClient.getBookSummary>>;

/**
 * #1091 on the summary page: signing out removes the summary from this browser.
 * Text typed within the one-second save delay is saved first; text that still
 * could not be saved is asked about; and a save that fails after the sign-out
 * does not write the text back.
 */

const WORKING = 'book-summary-book-1';
const UNSAVED = 'book-summary-unsaved-book-1';
const field = () => screen.getByPlaceholderText(/Describe your book/i) as HTMLTextAreaElement;

async function openedAndTyped(text: string) {
  const view = render(<BookSummaryPage />);
  await waitFor(() => expect(mockedClient.getBookSummary).toHaveBeenCalled());
  await act(async () => {});
  // Still inside the save delay: nothing has gone to the server yet.
  fireEvent.change(field(), { target: { value: text } });
  return view;
}

async function signOutAndLeave(view: ReturnType<typeof render>) {
  let signedOut = false;
  await act(async () => {
    signedOut = await signOutOrNotify();
  });
  if (signedOut) view.unmount();
  return signedOut;
}

let confirmSpy: jest.SpyInstance;

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  endSignOut();
  resetLeavingSavesForTests();
  jest.useFakeTimers();
  confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
  mockSignOut.mockResolvedValue({ data: {}, error: null });
  mockedClient.getBookSummary.mockResolvedValue({ summary: 'Saved', summary_history: [] } as SummaryResponse);
  mockedClient.saveBookSummary.mockImplementation(async (_book, summary) => ({ summary, success: true }) as never);
});

afterEach(() => {
  confirmSpy.mockRestore();
  jest.runOnlyPendingTimers();
  jest.useRealTimers();
});

describe('BookSummaryPage: signing out (#1091)', () => {
  it('saves text still inside the save delay before signing out, and leaves none behind', async () => {
    const view = await openedAndTyped('Typed just now');

    expect(await signOutAndLeave(view)).toBe(true);

    expect(mockedClient.saveBookSummary).toHaveBeenCalledWith('book-1', 'Typed just now');
    expect(mockedClient.saveBookSummary.mock.invocationCallOrder[0]).toBeLessThan(
      mockSignOut.mock.invocationCallOrder[0]
    );
    expect(confirmSpy).not.toHaveBeenCalled();
    expect(localStorage.getItem(WORKING)).toBeNull();
    expect(localStorage.getItem(UNSAVED)).toBeNull();
  });

  it('asks before removing text that could not be saved; no keeps it and stays signed in', async () => {
    mockedClient.saveBookSummary.mockRejectedValue(new Error('Network error'));
    confirmSpy.mockReturnValue(false);
    const view = await openedAndTyped('Never reached the server');

    expect(await signOutAndLeave(view)).toBe(false);

    expect(confirmSpy).toHaveBeenCalledWith(UNSAVED_WRITING_WARNING);
    expect(mockSignOut).not.toHaveBeenCalled();
    expect(localStorage.getItem(UNSAVED)).toBe('Never reached the server');
    view.unmount();
  });

  it('asks about text that could not be saved even when the browser could not keep a copy', async () => {
    mockedClient.saveBookSummary.mockRejectedValue(new Error('Network error'));
    confirmSpy.mockReturnValue(false);
    const view = await openedAndTyped('Never reached the server');
    const setItem = jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('Quota exceeded', 'QuotaExceededError');
    });

    expect(await signOutAndLeave(view)).toBe(false);

    setItem.mockRestore();
    expect(localStorage.getItem(UNSAVED)).toBeNull();
    expect(confirmSpy).toHaveBeenCalledWith(UNSAVED_WRITING_WARNING);
    expect(mockSignOut).not.toHaveBeenCalled();
    view.unmount();
  });

  it('leaving the page inside the save delay saves the text, and a later sign-out asks if that failed', async () => {
    let failLeaving: (err: Error) => void = () => {};
    mockedClient.saveBookSummary.mockImplementation(
      () => new Promise((_resolve, reject) => (failLeaving = reject)) as never
    );
    confirmSpy.mockReturnValue(false);
    const view = await openedAndTyped('Typed, then left');
    view.unmount();
    expect(mockedClient.saveBookSummary).toHaveBeenCalledWith('book-1', 'Typed, then left');

    let signedOut: Promise<boolean> = Promise.resolve(true);
    await act(async () => {
      signedOut = signOutOrNotify();
    });
    await act(async () => {
      failLeaving(new Error('Network error'));
    });

    expect(await signedOut).toBe(false);
    expect(confirmSpy).toHaveBeenCalledWith(UNSAVED_WRITING_WARNING);
    expect(localStorage.getItem(UNSAVED)).toBe('Typed, then left');
  });

  it('asks about a leaving save that failed while the browser could not keep a copy', async () => {
    mockedClient.saveBookSummary.mockRejectedValue(new Error('Network error'));
    confirmSpy.mockReturnValue(false);
    const view = await openedAndTyped('Typed, then left');
    const setItem = jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('Quota exceeded', 'QuotaExceededError');
    });
    view.unmount();
    await act(async () => {});
    setItem.mockRestore();
    expect(localStorage.getItem(UNSAVED)).toBeNull();

    let signedOut = true;
    await act(async () => {
      signedOut = await signOutOrNotify();
    });

    expect(signedOut).toBe(false);
    expect(confirmSpy).toHaveBeenCalledWith(UNSAVED_WRITING_WARNING);
    expect(mockSignOut).not.toHaveBeenCalled();
  });

  it('a leaving save waits behind a save still running, and sign-out waits for both', async () => {
    const view = await openedAndTyped('First');
    let finishFirst: (value: unknown) => void = () => {};
    mockedClient.saveBookSummary.mockImplementationOnce(
      () => new Promise((resolve) => (finishFirst = resolve)) as never
    );
    await act(async () => {
      jest.advanceTimersByTime(1000);
    });
    expect(mockedClient.saveBookSummary).toHaveBeenCalledTimes(1);

    // More typing, then the page closes while the first save still runs.
    fireEvent.change(field(), { target: { value: 'Second' } });
    view.unmount();
    await act(async () => {});
    expect(mockedClient.saveBookSummary).toHaveBeenCalledTimes(1);

    let signedOut: Promise<boolean> = Promise.resolve(false);
    await act(async () => {
      signedOut = signOutOrNotify();
    });
    expect(mockSignOut).not.toHaveBeenCalled();
    await act(async () => {
      finishFirst({ summary: 'First', success: true });
    });

    expect(await signedOut).toBe(true);
    expect(mockedClient.saveBookSummary).toHaveBeenLastCalledWith('book-1', 'Second');
    expect(mockedClient.saveBookSummary.mock.invocationCallOrder[1]).toBeLessThan(
      mockSignOut.mock.invocationCallOrder[0]
    );
    expect(confirmSpy).not.toHaveBeenCalled();
  });

  it('waits for a save in flight, and a save that fails after the sign-out writes nothing back', async () => {
    const view = await openedAndTyped('First');
    // The debounced save starts and is still running when the user signs out.
    // Every save fails: the server is away.
    mockedClient.saveBookSummary.mockRejectedValue(new Error('Network error'));
    let failFirst: (err: Error) => void = () => {};
    mockedClient.saveBookSummary.mockImplementationOnce(
      () => new Promise((_resolve, reject) => (failFirst = reject)) as never
    );
    await act(async () => {
      jest.advanceTimersByTime(1000);
    });
    expect(mockedClient.saveBookSummary).toHaveBeenCalledTimes(1);

    let signedOut: Promise<boolean> = Promise.resolve(false);
    await act(async () => {
      signedOut = signOutOrNotify();
    });
    // The sign-out has not gone ahead while the save runs.
    expect(mockSignOut).not.toHaveBeenCalled();
    await act(async () => {
      failFirst(new Error('Network error'));
    });
    expect(await signedOut).toBe(true);
    // Tried once more before the sign-out; it failed too and left its copy,
    // which the user was asked about and removed.
    expect(mockedClient.saveBookSummary).toHaveBeenCalledTimes(2);
    expect(confirmSpy).toHaveBeenCalledWith(UNSAVED_WRITING_WARNING);
    expect(localStorage.getItem(UNSAVED)).toBeNull();
    view.unmount();
  });

  it('a retry that fails long after the sign-out does not write the text back', async () => {
    mockedClient.saveBookSummary.mockRejectedValue(new Error('Network error'));
    const view = await openedAndTyped('Never reached the server');
    await act(async () => {
      jest.advanceTimersByTime(1000);
    });
    expect(localStorage.getItem(UNSAVED)).toBe('Never reached the server');

    // The sign-out request is slow; while it runs, the browser comes back online
    // and the page retries the failed save, which hangs.
    let finishSignOut: (value: unknown) => void = () => {};
    mockSignOut.mockImplementationOnce(() => new Promise((resolve) => (finishSignOut = resolve)));
    let signedOut: Promise<boolean> = Promise.resolve(false);
    await act(async () => {
      signedOut = signOutOrNotify();
    });
    expect(confirmSpy).toHaveBeenCalledWith(UNSAVED_WRITING_WARNING);
    expect(mockSignOut).toHaveBeenCalledTimes(1);
    let failRetry: (err: Error) => void = () => {};
    mockedClient.saveBookSummary.mockImplementationOnce(
      () => new Promise((_resolve, reject) => (failRetry = reject)) as never
    );
    await act(async () => {
      window.dispatchEvent(new Event('online'));
    });
    expect(mockedClient.saveBookSummary).toHaveBeenCalledTimes(3);
    await act(async () => {
      finishSignOut({ data: {}, error: null });
    });
    expect(await signedOut).toBe(true);
    view.unmount();

    // Well past the few seconds the sign-out holds the redirect guards.
    await act(async () => {
      jest.advanceTimersByTime(10_000);
      failRetry(new Error('Network error'));
    });

    expect(localStorage.getItem(UNSAVED)).toBeNull();
    expect(localStorage.getItem(WORKING)).toBeNull();
  });
  it('while the page is still up after the sign-out, nothing it does writes the text back', async () => {
    mockedClient.saveBookSummary.mockRejectedValue(new Error('Network error'));
    render(<BookSummaryPage />);
    await waitFor(() => expect(mockedClient.getBookSummary).toHaveBeenCalled());
    await act(async () => {});
    fireEvent.change(field(), { target: { value: 'Never reached the server' } });

    let signedOut = false;
    await act(async () => {
      signedOut = await signOutOrNotify();
    });
    expect(signedOut).toBe(true);
    expect(localStorage.getItem(UNSAVED)).toBeNull();

    // The caller's navigation has not landed yet: a keystroke (or a dictation
    // result), its debounced save, and the browser coming back online.
    fireEvent.change(field(), { target: { value: 'Typed after signing out' } });
    await act(async () => {
      jest.advanceTimersByTime(1000);
    });
    await act(async () => {
      window.dispatchEvent(new Event('online'));
    });
    await act(async () => {});

    expect(localStorage.getItem(WORKING)).toBeNull();
    expect(localStorage.getItem(UNSAVED)).toBeNull();
  });
});
