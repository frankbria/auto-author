/**
 * Closing a chapter's tab hides it until the writer reopens it (#1043).
 *
 * A closed chapter used to be a chapter missing from the saved order, which
 * #830 reads as "new, give it a tab", so it came back on every reload and
 * refresh. The saved state now names the closed ones.
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

const BOOK = 'book-1043';

const toc = (...ids: string[]) => ({
  toc: {
    chapters: ids.map((id, index) => ({ id, title: `Chapter ${id}`, level: 1, order: index + 1, subchapters: [] })),
    total_chapters: ids.length,
    estimated_pages: 1,
    structure_notes: '',
  },
});

const saved = (active: string, open: string[], order: string[], closed?: string[]) => ({
  active_chapter_id: active,
  open_tab_ids: open,
  tab_order: order,
  ...(closed ? { closed_tab_ids: closed } : {}),
});

async function loaded() {
  const hook = renderHook(() => useChapterTabs(BOOK));
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

describe('reconcileTabState with closed tabs', () => {
  it('gives a new chapter a tab but not a closed one', () => {
    expect(reconcileTabState(['c1', 'c2', 'c3', 'c4'], saved('c1', ['c1'], ['c1'], ['c2']))).toEqual({
      active_chapter_id: 'c1',
      open_tab_ids: ['c1'],
      tab_order: ['c1', 'c3', 'c4'],
      closed_tab_ids: ['c2'],
    });
  });

  it('drops a deleted chapter from the closed ones', () => {
    expect(reconcileTabState(['c1', 'c3'], saved('c1', ['c1'], ['c1'], ['c2', 'c3'])).closed_tab_ids).toEqual(['c3']);
  });

  it('behaves as before for a state saved without the field', () => {
    expect(reconcileTabState(['c1', 'c2'], saved('c1', ['c1'], ['c1']))).toEqual({
      active_chapter_id: 'c1',
      open_tab_ids: ['c1'],
      tab_order: ['c1', 'c2'],
      closed_tab_ids: [],
    });
  });

  it('opens the chapter a link names even if it was closed', () => {
    const r = reconcileTabState(['c1', 'c2'], saved('c1', ['c1'], ['c1'], ['c2']), 'c2');
    expect(r.open_tab_ids).toEqual(['c1', 'c2']);
    expect(r.closed_tab_ids).toEqual([]);
    expect(r.tab_order).toEqual(['c1', 'c2']);
  });
});

describe('useChapterTabs with closed tabs', () => {
  it('keeps a closed chapter closed across a reload', async () => {
    const first = await loaded();
    act(() => first.result.current.actions.closeTab('c2'));
    expect(first.result.current.state.closed_tab_ids).toEqual(['c2']);
    await waitFor(() => expect(bookClient.saveTabState).toHaveBeenCalled(), { timeout: 3000 });
    const body = (bookClient.saveTabState as jest.Mock).mock.calls.at(-1)[1];
    expect(body.closed_tab_ids).toEqual(['c2']);
    first.unmount();

    (bookClient.getTabState as jest.Mock).mockResolvedValue({ tab_state: body });
    const second = await loaded();

    expect(second.result.current.state.tab_order).toEqual(['c1', 'c3']);
    expect(second.result.current.state.closed_tab_ids).toEqual(['c2']);
  });

  it('keeps it closed when the table of contents refreshes, and still tabs a new chapter', async () => {
    const { result } = await loaded();
    act(() => result.current.actions.closeTab('c2'));
    (bookClient.getToc as jest.Mock).mockResolvedValue(toc('c1', 'c2', 'c3', 'c4'));

    await act(async () => {
      await result.current.actions.refreshChapters();
    });

    expect(result.current.state.tab_order).toEqual(['c1', 'c3', 'c4']);
  });

  it('reopens a closed chapter and opens it', async () => {
    const { result } = await loaded();
    act(() => result.current.actions.closeTab('c2'));

    act(() => result.current.actions.openTab('c2'));

    expect(result.current.state.closed_tab_ids).toEqual([]);
    expect(result.current.state.open_tab_ids).toContain('c2');
    expect(result.current.state.tab_order).toContain('c2');
    expect(result.current.state.active_chapter_id).toBe('c2');
  });
});
