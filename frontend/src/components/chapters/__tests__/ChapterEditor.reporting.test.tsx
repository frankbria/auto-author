/**
 * A chapter that could not be saved, backed up or restored is reported (#813).
 *
 * These failures went to `console.error` and nowhere else. A writer whose
 * chapters stop saving is the failure this product can least afford to miss,
 * and nobody would have been told. Each is now sent to Sentry with the tag
 * `feature: 'autosave'` and never with the chapter's text.
 */
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import * as Sentry from '@sentry/nextjs';
import { ChapterEditor } from '../ChapterEditor';
import { flushChapterContent, saveSucceeded } from '../chapterContentSave';
import bookClient from '@/lib/api/bookClient';

jest.mock('@/lib/api/bookClient');
jest.mock('../DraftGenerator', () => ({
  DraftGenerator: () => <div>Draft Generator</div>,
}));

const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;
const captured = Sentry.captureException as jest.Mock;

type ChapterContent = Awaited<ReturnType<typeof bookClient.getChapterContent>>;
const chapterContent = (content: string) => ({ content } as ChapterContent);

const TYPED = 'MANUSCRIPT-SENTINEL a sentence of the chapter';
const props = { bookId: 'book-1', chapterId: 'chapter-1', chapterTitle: 'Test Chapter', initialContent: '<p>Start</p>' };

const reports = () => captured.mock.calls.map(([, context]) => context?.tags);

async function typeAndWaitForAutosave() {
  const user = userEvent.setup({ delay: null });
  render(<ChapterEditor {...props} />);
  await waitFor(() => expect(screen.getByRole('textbox')).toBeInTheDocument());
  await user.type(screen.getByRole('textbox'), TYPED);
  await act(async () => {
    jest.advanceTimersByTime(3000);
    await Promise.resolve();
  });
  return user;
}

describe('ChapterEditor reports what it could not save', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    saveSucceeded(); // what has been reported is kept for the page, not per test
    jest.useFakeTimers();
    jest.spyOn(console, 'error').mockImplementation(() => {});
    mockBookClient.getChapterContent.mockResolvedValue(chapterContent('<p>Start</p>'));
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  it('an autosave that fails', async () => {
    const failure = new Error('Failed to save chapter content: 500');
    mockBookClient.saveChapterContent.mockRejectedValue(failure);

    await typeAndWaitForAutosave();

    await waitFor(() => expect(captured).toHaveBeenCalledTimes(1));
    expect(captured).toHaveBeenCalledWith(failure, { tags: { feature: 'autosave', operation: 'auto-save' } });
  });

  it('once for a run of failed autosaves, which retry every few seconds while the server is away', async () => {
    mockBookClient.saveChapterContent.mockRejectedValue(new Error('Failed to save chapter content: 500'));

    await typeAndWaitForAutosave();
    await waitFor(() => expect(mockBookClient.saveChapterContent).toHaveBeenCalledTimes(1));
    for (const attempt of [2, 3]) {
      await act(async () => {
        jest.advanceTimersByTime(3000);
        await Promise.resolve();
      });
      await waitFor(() => expect(mockBookClient.saveChapterContent).toHaveBeenCalledTimes(attempt));
    }

    expect(reports()).toEqual([{ feature: 'autosave', operation: 'auto-save' }]);
  });

  it('once for the backup too, when it cannot be written on any of those retries', async () => {
    mockBookClient.saveChapterContent.mockRejectedValue(new Error('Failed to save chapter content: 500'));
    jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('The quota has been exceeded.', 'QuotaExceededError');
    });

    await typeAndWaitForAutosave();
    await waitFor(() => expect(mockBookClient.saveChapterContent).toHaveBeenCalledTimes(1));
    for (const attempt of [2, 3]) {
      await act(async () => {
        jest.advanceTimersByTime(3000);
        await Promise.resolve();
      });
      await waitFor(() => expect(mockBookClient.saveChapterContent).toHaveBeenCalledTimes(attempt));
    }

    expect(reports()).toEqual([
      { feature: 'autosave', operation: 'auto-save' },
      { feature: 'autosave', operation: 'backup' },
    ]);
  });

  it('again after five minutes of it, so a long outage is not one report and silence', async () => {
    mockBookClient.saveChapterContent.mockRejectedValue(new Error('Failed to save chapter content: 500'));

    await typeAndWaitForAutosave();
    await waitFor(() => expect(reports()).toHaveLength(1));
    await act(async () => {
      jest.advanceTimersByTime(5 * 60 * 1000);
      await Promise.resolve();
    });

    await waitFor(() => expect(reports()).toHaveLength(2));
  });

  it('again when saving has worked in between', async () => {
    mockBookClient.saveChapterContent
      .mockRejectedValueOnce(new Error('Failed to save chapter content: 500'))
      .mockResolvedValueOnce({} as Awaited<ReturnType<typeof bookClient.saveChapterContent>>)
      .mockRejectedValue(new Error('Failed to save chapter content: 502'));

    const user = await typeAndWaitForAutosave();
    await waitFor(() => expect(mockBookClient.saveChapterContent).toHaveBeenCalledTimes(1));
    await act(async () => {
      jest.advanceTimersByTime(3000);
      await Promise.resolve();
    });
    await waitFor(() => expect(mockBookClient.saveChapterContent).toHaveBeenCalledTimes(2));
    await user.type(screen.getByRole('textbox'), ' and more');
    await act(async () => {
      jest.advanceTimersByTime(3000);
      await Promise.resolve();
    });
    await waitFor(() => expect(mockBookClient.saveChapterContent).toHaveBeenCalledTimes(3));

    await waitFor(() => expect(reports()).toHaveLength(2));
  });

  it('a save the writer asked for that fails', async () => {
    const failure = new Error('Failed to save chapter content: 503');
    mockBookClient.saveChapterContent.mockRejectedValue(failure);
    const user = userEvent.setup({ delay: null });
    render(<ChapterEditor {...props} />);
    await waitFor(() => expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /save/i }));

    await waitFor(() => expect(captured).toHaveBeenCalledTimes(1));
    expect(captured).toHaveBeenCalledWith(failure, { tags: { feature: 'autosave', operation: 'manual-save' } });
  });

  it('never sends the chapter with it', async () => {
    mockBookClient.saveChapterContent.mockRejectedValue(new Error('Failed to save chapter content: 500'));

    await typeAndWaitForAutosave();

    await waitFor(() => expect(captured).toHaveBeenCalled());
    const sent = JSON.stringify(captured.mock.calls.map(([error, context]) => [String(error), context]));
    expect(sent).not.toContain('MANUSCRIPT-SENTINEL');
  });

  it('a backup that could not be written either, which is the case where the text exists nowhere else', async () => {
    mockBookClient.saveChapterContent.mockRejectedValue(new Error('Failed to save chapter content: 500'));
    jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('The quota has been exceeded.', 'QuotaExceededError');
    });

    await typeAndWaitForAutosave();

    await waitFor(() => expect(reports()).toHaveLength(2));
    expect(reports()).toEqual([
      { feature: 'autosave', operation: 'auto-save' },
      { feature: 'autosave', operation: 'backup' },
    ]);
  });

  it('a backup that could not be restored', async () => {
    localStorage.setItem(
      'chapter-backup-book-1-chapter-1',
      JSON.stringify({ content: `<p>${TYPED}</p>`, timestamp: Date.now() - 60000, error: 'Network error' })
    );
    mockBookClient.saveChapterContent.mockResolvedValue({} as Awaited<ReturnType<typeof bookClient.saveChapterContent>>);
    const user = userEvent.setup({ delay: null });
    render(<ChapterEditor {...props} />);
    await waitFor(() => expect(screen.getByRole('button', { name: /restore backup/i })).toBeInTheDocument());
    jest.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
      throw new Error('Storage is not available');
    });

    await user.click(screen.getByRole('button', { name: /restore backup/i }));

    await waitFor(() => expect(reports()).toEqual([{ feature: 'autosave', operation: 'restore' }]));
    expect(JSON.stringify(captured.mock.calls.map(([error, context]) => [String(error), context]))).not.toContain(
      'MANUSCRIPT-SENTINEL'
    );
  });

  it('not a save that lost to another copy: that is an answer, and the writer is asked what to do', async () => {
    mockBookClient.saveChapterContent.mockRejectedValue(
      Object.assign(new Error('This chapter was saved from somewhere else since you opened it.'), {
        statusCode: 409,
        currentContent: '<p>Their copy</p>',
        currentLastModified: 't2',
      })
    );

    await typeAndWaitForAutosave();

    await waitFor(() => expect(mockBookClient.saveChapterContent).toHaveBeenCalled());
    await act(async () => {
      await Promise.resolve();
    });
    expect(captured).not.toHaveBeenCalled();
  });
});

describe('leaving a chapter with an edit that cannot be saved', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    saveSucceeded();
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => jest.restoreAllMocks());

  it('is reported, since nothing is left on screen to say so', async () => {
    const failure = new Error('Failed to save chapter content: 500');
    mockBookClient.saveChapterContent.mockRejectedValue(failure);

    await flushChapterContent({ bookId: 'book-1', chapterId: 'chapter-1', content: `<p>${TYPED}</p>` }, new Map());

    expect(captured).toHaveBeenCalledWith(failure, { tags: { feature: 'autosave', operation: 'leave-save' } });
    expect(localStorage.getItem('chapter-backup-book-1-chapter-1')).toContain('MANUSCRIPT-SENTINEL');
  });
});
