/**
 * A failing autosave backs off instead of retrying every 3 seconds (#855).
 *
 * While the server was away, each failed save re-armed the same 3s timer, so an
 * open editor sent a request every 3 seconds for as long as the outage lasted.
 * Each consecutive failure now doubles the wait, and a save that works resets it.
 */
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChapterEditor } from '../ChapterEditor';
import { saveSucceeded } from '../chapterContentSave';
import bookClient from '@/lib/api/bookClient';

jest.mock('@/lib/api/bookClient');
jest.mock('../DraftGenerator', () => ({
  DraftGenerator: () => <div>Draft Generator</div>,
}));

const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;
type Saved = Awaited<ReturnType<typeof bookClient.saveChapterContent>>;
const props = { bookId: 'book-1', chapterId: 'chapter-1', chapterTitle: 'Test Chapter', initialContent: '<p>Start</p>' };

async function advance(ms: number) {
  await act(async () => {
    jest.advanceTimersByTime(ms);
    await Promise.resolve();
  });
}

const saves = () => mockBookClient.saveChapterContent.mock.calls.length;

describe('ChapterEditor autosave backoff (#855)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    saveSucceeded();
    jest.useFakeTimers();
    jest.spyOn(console, 'error').mockImplementation(() => {});
    mockBookClient.getChapterContent.mockResolvedValue({ content: '<p>Start</p>' } as Awaited<
      ReturnType<typeof bookClient.getChapterContent>
    >);
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  async function typeSomething() {
    const user = userEvent.setup({ delay: null });
    render(<ChapterEditor {...props} />);
    await waitFor(() => expect(screen.getByRole('textbox')).toBeInTheDocument());
    await user.type(screen.getByRole('textbox'), 'a sentence of the chapter');
    return user;
  }

  it('waits twice as long after each failed save', async () => {
    mockBookClient.saveChapterContent.mockRejectedValue(new Error('Failed to save chapter content: 503'));
    await typeSomething();

    await advance(3000);
    await waitFor(() => expect(saves()).toBe(1));

    await advance(3000);
    expect(saves()).toBe(1); // not yet: the second try waits 6s
    await advance(3000);
    await waitFor(() => expect(saves()).toBe(2));

    await advance(11000);
    expect(saves()).toBe(2); // the third waits 12s
    await advance(1000);
    await waitFor(() => expect(saves()).toBe(3));
  });

  it('goes back to the normal delay once a save works', async () => {
    mockBookClient.saveChapterContent
      .mockRejectedValueOnce(new Error('Failed to save chapter content: 503'))
      .mockResolvedValue({} as Saved);
    const user = await typeSomething();

    await advance(3000);
    await waitFor(() => expect(saves()).toBe(1));
    await advance(6000);
    await waitFor(() => expect(saves()).toBe(2));

    await user.type(screen.getByRole('textbox'), ' and more');
    await advance(3000);
    await waitFor(() => expect(saves()).toBe(3));
  });

  it('never waits more than 30 seconds', async () => {
    mockBookClient.saveChapterContent.mockRejectedValue(new Error('Failed to save chapter content: 503'));
    await typeSomething();

    // Tries at 3s, then 6s, 12s and 24s later; the next is capped at 30s, not 48s.
    for (const [wait, attempts] of [[3000, 1], [6000, 2], [12000, 3], [24000, 4], [30000, 5]] as const) {
      await advance(wait);
      await waitFor(() => expect(saves()).toBe(attempts));
    }
  });

  it('goes back to the normal delay after a manual save that works', async () => {
    mockBookClient.saveChapterContent
      .mockRejectedValueOnce(new Error('Failed to save chapter content: 503'))
      .mockResolvedValue({} as Saved);
    const user = await typeSomething();
    await advance(3000);
    await waitFor(() => expect(saves()).toBe(1));

    await act(async () => {
      screen.getByRole('button', { name: /^save$/i }).click();
    });
    await waitFor(() => expect(saves()).toBe(2));

    await user.type(screen.getByRole('textbox'), ' and more');
    await advance(3000);
    await waitFor(() => expect(saves()).toBe(3));
  });

  it('keeps the backup current while saves are failing', async () => {
    mockBookClient.saveChapterContent.mockRejectedValue(new Error('Failed to save chapter content: 503'));
    const user = await typeSomething();
    await advance(3000);
    await waitFor(() => expect(saves()).toBe(1));

    // The next try is 6s away; what is typed meanwhile is backed up at once.
    await user.type(screen.getByRole('textbox'), ' typed during the wait');

    const backup = JSON.parse(localStorage.getItem('chapter-backup-book-1-chapter-1') ?? '{}');
    expect(backup.content).toContain('typed during the wait');
    expect(saves()).toBe(1);
  });
});
