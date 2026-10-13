/**
 * Saved tab state is reconciled with the table of contents, and a link to a
 * chapter wins over it (#830).
 *
 * The tabs a reader had open are saved, in the browser and on the server, and
 * restored on the next visit. They were restored as they were: a chapter added
 * since was in no saved order, so it had no tab; a chapter deleted since could
 * still be the active one, with nothing to show; and a `?chapter=` link opened
 * whatever chapter was active last time instead of the one it names.
 */
import { renderHook, waitFor, act } from '@testing-library/react';
import { useChapterTabs } from '../useChapterTabs';
import bookClient from '@/lib/api/bookClient';
import { reconcileTabState } from '@/lib/utils/reconcileTabState';

jest.mock('@/lib/api/bookClient', () => ({
  __esModule: true,
  default: {
    getToc: jest.fn(),
    getChaptersMetadata: jest.fn(),
    getTabState: jest.fn(),
    saveTabState: jest.fn(),
    updateChapterStatus: jest.fn(),
  },
}));

const BOOK = 'book-830';

const toc = (...ids: string[]) => ({
  toc: {
    chapters: ids.map((id, index) => ({ id, title: `Chapter ${id}`, level: 1, order: index + 1, subchapters: [] })),
    total_chapters: ids.length,
    estimated_pages: 1,
    structure_notes: '',
  },
});

const saved = (active: string | null, open: string[], order: string[]) => ({
  active_chapter_id: active,
  open_tab_ids: open,
  tab_order: order,
});

async function loaded(initialActiveChapter?: string) {
  const hook = renderHook(() => useChapterTabs(BOOK, initialActiveChapter));
  await waitFor(() => expect(hook.result.current.state.is_loading).toBe(false));
  return hook;
}

beforeEach(() => {
  jest.clearAllMocks();
  window.localStorage.clear();
  (bookClient.getToc as jest.Mock).mockResolvedValue(toc('c1', 'c2', 'c3'));
  (bookClient.getTabState as jest.Mock).mockResolvedValue(null);
  (bookClient.saveTabState as jest.Mock).mockResolvedValue({});
});

describe('reconcileTabState', () => {
  it('reconciles saved [c1, c2] with a table of contents of c1 to c3 when the active chapter is gone', () => {
    expect(reconcileTabState(['c1', 'c2', 'c3'], saved('gone', ['c1', 'c2'], ['c1', 'c2']))).toEqual({
      active_chapter_id: 'c1',
      open_tab_ids: ['c1', 'c2'],
      tab_order: ['c1', 'c2', 'c3'],
    });
  });

  it('drops chapters that are no longer there, from the open tabs and from the order', () => {
    expect(reconcileTabState(['c2', 'c3'], saved('c2', ['c1', 'c2'], ['c1', 'c2', 'c3']))).toEqual({
      active_chapter_id: 'c2',
      open_tab_ids: ['c2'],
      tab_order: ['c2', 'c3'],
    });
  });

  it('keeps the order the reader gave the tabs and puts new chapters after it', () => {
    expect(reconcileTabState(['c1', 'c2', 'c3', 'c4'], saved('c3', ['c3', 'c1'], ['c3', 'c1'])).tab_order).toEqual([
      'c3', 'c1', 'c2', 'c4',
    ]);
  });

  it('makes the chapter that was asked for the active one, and opens it', () => {
    expect(reconcileTabState(['c1', 'c2', 'c3'], saved('c1', ['c1'], ['c1', 'c2', 'c3']), 'c3')).toEqual({
      active_chapter_id: 'c3',
      open_tab_ids: ['c1', 'c3'],
      tab_order: ['c1', 'c2', 'c3'],
    });
  });

  it('ignores a chapter that was asked for but is not in the book', () => {
    expect(reconcileTabState(['c1', 'c2'], saved('c2', ['c2'], ['c1', 'c2']), 'gone').active_chapter_id).toBe('c2');
  });

  it('starts on the first chapter when nothing was saved', () => {
    expect(reconcileTabState(['c1', 'c2'], {})).toEqual({
      active_chapter_id: 'c1',
      open_tab_ids: ['c1'],
      tab_order: ['c1', 'c2'],
    });
  });

  it('lists a chapter once however often the saved state names it', () => {
    expect(reconcileTabState(['c1', 'c2'], saved('c1', ['c1', 'c1'], ['c2', 'c1', 'c2']))).toEqual({
      active_chapter_id: 'c1',
      open_tab_ids: ['c1'],
      tab_order: ['c2', 'c1'],
    });
  });

  it('has nothing active in a book with no chapters', () => {
    expect(reconcileTabState([], saved('c1', ['c1'], ['c1']))).toEqual({
      active_chapter_id: null,
      open_tab_ids: [],
      tab_order: [],
    });
  });
});

describe('useChapterTabs on load', () => {
  it('opens the chapter the link names, not the one that was active last time', async () => {
    (bookClient.getTabState as jest.Mock).mockResolvedValue(saved('c1', ['c1'], ['c1', 'c2', 'c3']));

    const { result } = await loaded('c3');

    expect(result.current.state.active_chapter_id).toBe('c3');
    expect(result.current.state.open_tab_ids).toEqual(['c1', 'c3']);
  });

  it('does the same when the last visit was saved in the browser', async () => {
    window.localStorage.setItem(
      `tabState_${BOOK}`,
      JSON.stringify({ ...saved('c2', ['c2'], ['c1', 'c2', 'c3']), last_updated: new Date().toISOString() }),
    );

    const { result } = await loaded('c3');

    expect(result.current.state.active_chapter_id).toBe('c3');
  });

  it('still opens the chapter that was active last time when no link names one', async () => {
    (bookClient.getTabState as jest.Mock).mockResolvedValue(saved('c2', ['c1', 'c2'], ['c1', 'c2', 'c3']));

    const { result } = await loaded();

    expect(result.current.state.active_chapter_id).toBe('c2');
    expect(result.current.state.open_tab_ids).toEqual(['c1', 'c2']);
  });

  it('gives a chapter added since the last visit a tab, and does not stay on one that was deleted', async () => {
    (bookClient.getTabState as jest.Mock).mockResolvedValue(saved('gone', ['c1', 'c2'], ['c1', 'c2']));

    const { result } = await loaded();

    expect(result.current.state.tab_order).toEqual(['c1', 'c2', 'c3']);
    expect(result.current.state.open_tab_ids).toEqual(['c1', 'c2']);
    expect(result.current.state.active_chapter_id).toBe('c1');
  });
});

describe('useChapterTabs on refresh', () => {
  it('reconciles the same way when the table of contents changes under it', async () => {
    (bookClient.getTabState as jest.Mock).mockResolvedValue(saved('c2', ['c1', 'c2'], ['c2', 'c1', 'c3']));
    const { result } = await loaded();
    (bookClient.getToc as jest.Mock).mockResolvedValue(toc('c1', 'c3', 'c4'));

    await act(async () => {
      await result.current.actions.refreshChapters();
    });

    expect(result.current.state.tab_order).toEqual(['c1', 'c3', 'c4']);
    expect(result.current.state.open_tab_ids).toEqual(['c1']);
    expect(result.current.state.active_chapter_id).toBe('c1');
  });
});
