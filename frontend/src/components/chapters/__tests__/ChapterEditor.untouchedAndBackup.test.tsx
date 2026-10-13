/**
 * Opening a chapter is not editing it, and a backup does not quietly replace
 * newer saved text (#831).
 *
 * Putting the loaded text into the editor counted as an edit: every chapter
 * opened and left untouched was marked unsaved, saved again three seconds
 * later, and the browser asked before the page was left. Restore Backup put a
 * backup of any age over whatever the server held. And backups past their
 * week were never cleared out.
 */
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChapterEditor } from '../ChapterEditor';
import bookClient from '@/lib/api/bookClient';

jest.mock('@/lib/api/bookClient');
jest.mock('../DraftGenerator', () => ({
  DraftGenerator: () => <div>Draft Generator</div>,
}));

const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;
type ChapterContent = Awaited<ReturnType<typeof bookClient.getChapterContent>>;

const HOUR = 60 * 60 * 1000;
const DAY = 24 * HOUR;
const props = { bookId: 'book-1', chapterId: 'chapter-1', chapterTitle: 'The Keeper' };
const BACKUP_KEY = 'chapter-backup-book-1-chapter-1';

/** The server's copy, last saved ``ago`` milliseconds before now (null: never saved). */
function serverHas(content: string, ago: number | null = HOUR) {
  mockBookClient.getChapterContent.mockResolvedValue({
    content,
    last_modified: ago === null ? null : new Date(Date.now() - ago).toISOString(),
  } as ChapterContent);
}

function backupFrom(ago: number, content = '<p>The backup</p>', key = BACKUP_KEY) {
  localStorage.setItem(key, JSON.stringify({ content, timestamp: Date.now() - ago }));
}

async function opened() {
  const view = render(<ChapterEditor {...props} />);
  await waitFor(() => expect((screen.getByRole('textbox') as HTMLTextAreaElement).value).not.toBe(''));
  return view;
}

/** The editor's test double does not redraw restored text, so it is read from the save that follows. */
async function expectTheBackupToBeWhatIsSaved() {
  await act(async () => {
    jest.advanceTimersByTime(3000);
    await Promise.resolve();
  });
  await waitFor(() =>
    expect(mockBookClient.saveChapterContent).toHaveBeenCalledWith(
      'book-1',
      'chapter-1',
      '<p>The backup</p>',
      expect.anything(),
      expect.anything(),
    ),
  );
}

/** Whether the browser would ask before leaving the page. */
function asksBeforeLeaving(): boolean {
  const leaving = new Event('beforeunload', { cancelable: true });
  window.dispatchEvent(leaving);
  return leaving.defaultPrevented;
}

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  jest.useFakeTimers();
  mockBookClient.saveChapterContent.mockResolvedValue({} as Awaited<ReturnType<typeof bookClient.saveChapterContent>>);
});

afterEach(() => {
  jest.runOnlyPendingTimers();
  jest.useRealTimers();
});

describe('a chapter that is opened and not touched', () => {
  it('does not make the browser ask before the page is left', async () => {
    serverHas('<p>Saved text</p>');
    await opened();

    expect(asksBeforeLeaving()).toBe(false);
  });

  it('is not saved again', async () => {
    serverHas('<p>Saved text</p>');
    await opened();

    await act(async () => {
      jest.advanceTimersByTime(10_000);
      await Promise.resolve();
    });

    expect(mockBookClient.saveChapterContent).not.toHaveBeenCalled();
  });

  it('is not marked unsaved when the page hands the editor new text either', async () => {
    serverHas('<p>Unused</p>');
    const view = render(<ChapterEditor {...props} initialContent="<p>First text</p>" />);
    await waitFor(() => expect(screen.getByRole('textbox')).toHaveValue('<p>First text</p>'));

    view.rerender(<ChapterEditor {...props} initialContent="<p>Second text</p>" />);
    await act(async () => {
      await Promise.resolve();
    });

    expect(asksBeforeLeaving()).toBe(false);
  });

  it('still asks once something has been typed', async () => {
    const user = userEvent.setup({ delay: null });
    serverHas('<p>Saved text</p>');
    await opened();

    await user.type(screen.getByRole('textbox'), ' and more');

    expect(asksBeforeLeaving()).toBe(true);
  });
});

describe('restoring a backup', () => {
  it('asks first when the backup is older than what is saved', async () => {
    const user = userEvent.setup({ delay: null });
    backupFrom(3 * DAY);
    serverHas('<p>Saved since</p>', HOUR);
    await opened();

    await user.click(screen.getByRole('button', { name: /restore backup/i }));

    expect(screen.getByRole('textbox')).toHaveValue('<p>Saved since</p>');
    expect(screen.getByText(/older than the saved chapter/i)).toBeInTheDocument();
    expect(localStorage.getItem(BACKUP_KEY)).not.toBeNull();
  });

  it('restores it when the writer says so', async () => {
    const user = userEvent.setup({ delay: null });
    backupFrom(3 * DAY);
    serverHas('<p>Saved since</p>', HOUR);
    await opened();
    await user.click(screen.getByRole('button', { name: /restore backup/i }));

    await user.click(screen.getByRole('button', { name: /restore the older backup/i }));

    await expectTheBackupToBeWhatIsSaved();
    expect(localStorage.getItem(BACKUP_KEY)).toBeNull();
    expect(screen.queryByText(/older than the saved chapter/i)).not.toBeInTheDocument();
  });

  it('offers a later backup plainly, not with the question the earlier one raised', async () => {
    const user = userEvent.setup({ delay: null });
    backupFrom(3 * DAY);
    serverHas('<p>Saved since</p>', HOUR);
    await opened();
    await user.click(screen.getByRole('button', { name: /restore backup/i }));
    await user.click(screen.getByRole('button', { name: /restore the older backup/i }));

    // A save fails later and leaves a new backup; typing makes the editor look again.
    backupFrom(0, '<p>A later backup</p>');
    await user.type(screen.getByRole('textbox'), '!');

    expect(await screen.findByRole('button', { name: /^restore backup$/i })).toBeInTheDocument();
    expect(screen.queryByText(/older than the saved chapter/i)).not.toBeInTheDocument();
  });

  it('does not carry the question over to another chapter shown in the same editor', async () => {
    const user = userEvent.setup({ delay: null });
    backupFrom(3 * DAY);
    backupFrom(3 * DAY, '<p>Chapter two, three days ago</p>', 'chapter-backup-book-1-chapter-2');
    serverHas('<p>Saved since</p>', HOUR);
    const view = await opened();
    await user.click(screen.getByRole('button', { name: /restore backup/i }));
    expect(screen.getByText(/older than the saved chapter/i)).toBeInTheDocument();

    view.rerender(<ChapterEditor {...props} chapterId="chapter-2" chapterTitle="The First Letter" />);

    // The second chapter's backup is offered plainly, and pressing Restore asks about it afresh.
    const restore = await screen.findByRole('button', { name: /^restore backup$/i });
    expect(screen.queryByRole('button', { name: /restore the older backup/i })).not.toBeInTheDocument();
    await user.click(restore);
    expect(screen.getByText(/older than the saved chapter/i)).toBeInTheDocument();
    expect(localStorage.getItem('chapter-backup-book-1-chapter-2')).not.toBeNull();
  });

  it('keeps the saved text, and the backup, when the writer says not to', async () => {
    const user = userEvent.setup({ delay: null });
    backupFrom(3 * DAY);
    serverHas('<p>Saved since</p>', HOUR);
    await opened();
    await user.click(screen.getByRole('button', { name: /restore backup/i }));

    await user.click(screen.getByRole('button', { name: /keep the saved text/i }));

    expect(screen.getByRole('textbox')).toHaveValue('<p>Saved since</p>');
    expect(localStorage.getItem(BACKUP_KEY)).not.toBeNull();
    expect(screen.queryByText(/older than the saved chapter/i)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /restore backup/i })).toBeInTheDocument();
  });

  it('does not ask when the backup is the newer of the two: a save that failed', async () => {
    const user = userEvent.setup({ delay: null });
    backupFrom(HOUR);
    serverHas('<p>Saved before</p>', 3 * DAY);
    await opened();

    await user.click(screen.getByRole('button', { name: /restore backup/i }));

    await expectTheBackupToBeWhatIsSaved();
    expect(screen.queryByText(/older than the saved chapter/i)).not.toBeInTheDocument();
  });

  it('does not ask for a chapter that has never been saved', async () => {
    const user = userEvent.setup({ delay: null });
    backupFrom(HOUR);
    serverHas('<p>Placeholder</p>', null);
    await opened();

    await user.click(screen.getByRole('button', { name: /restore backup/i }));

    await expectTheBackupToBeWhatIsSaved();
  });
});

describe('backups past their week', () => {
  it('are removed when the editor opens, for this chapter and for others', async () => {
    backupFrom(8 * DAY);
    backupFrom(9 * DAY, '<p>Another chapter</p>', 'chapter-backup-book-7-chapter-7');
    backupFrom(8 * DAY, '<p>Dropped text</p>', 'chapter-dropped-book-7-chapter-7');
    serverHas('<p>Saved text</p>');

    await opened();

    expect(localStorage.getItem(BACKUP_KEY)).toBeNull();
    expect(localStorage.getItem('chapter-backup-book-7-chapter-7')).toBeNull();
    expect(localStorage.getItem('chapter-dropped-book-7-chapter-7')).toBeNull();
    expect(screen.queryByRole('button', { name: /restore backup/i })).not.toBeInTheDocument();
  });

  it('leaves a backup that is still within its week, and anything that is not a backup', async () => {
    backupFrom(6 * DAY);
    localStorage.setItem('tabState_book-1', JSON.stringify({ active_chapter_id: 'chapter-1' }));
    serverHas('<p>Saved text</p>', 7 * DAY);

    await opened();

    expect(localStorage.getItem(BACKUP_KEY)).not.toBeNull();
    expect(localStorage.getItem('tabState_book-1')).not.toBeNull();
    expect(screen.getByRole('button', { name: /restore backup/i })).toBeInTheDocument();
  });
});
