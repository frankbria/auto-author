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
});
