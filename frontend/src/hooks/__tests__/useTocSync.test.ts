/**
 * Tests for useTocSync hook and triggerTocUpdateEvent utility
 *
 * Coverage targets:
 * - generateTocHash: consistent results, subchapters, null toc, API errors
 * - checkForTocChanges: calls onTocChanged only when hash changes
 * - tocUpdated event listener: filtered by bookId, removed on unmount
 * - storage event listener: matching key, null guard, flag cleared, removed on unmount
 * - polling: init hash, change detection, no-change case, cleanup on unmount
 * - triggerTocUpdateEvent: dispatches event, sets localStorage
 */

import { renderHook, act } from '@testing-library/react';
import { useTocSync, triggerTocUpdateEvent } from '../useTocSync';
import bookClient from '@/lib/api/bookClient';

jest.mock('@/lib/api/bookClient', () => ({
  __esModule: true,
  default: {
    getToc: jest.fn(),
  },
}));

const mockGetToc = bookClient.getToc as jest.Mock;

const BOOK_ID = 'book-test-123';
const OTHER_BOOK_ID = 'book-other-456';

/** Flush all pending micro-tasks (mock Promise resolutions) */
async function flushPromises() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
}

function makeToc(chapters: Array<{ id: string; title?: string; order?: number; subchapters?: Array<{ id: string; title?: string; order?: number }> }>) {
  return {
    toc: {
      chapters: chapters.map((ch, i) => ({
        id: ch.id,
        title: ch.title ?? `Chapter ${i + 1}`,
        order: ch.order ?? i + 1,
        subchapters: (ch.subchapters ?? []).map((sub, j) => ({
          id: sub.id,
          title: sub.title ?? `Sub ${j + 1}`,
          order: sub.order ?? j + 1,
        })),
      })),
    },
  };
}

const SIMPLE_TOC = makeToc([{ id: 'ch-1' }, { id: 'ch-2' }]);
const MODIFIED_TOC = makeToc([{ id: 'ch-1' }, { id: 'ch-2' }, { id: 'ch-3' }]);
const TOC_WITH_SUBCHAPTERS = makeToc([
  { id: 'ch-1', subchapters: [{ id: 'sub-1' }, { id: 'sub-2' }] },
]);
const TOC_MODIFIED_SUBCHAPTERS = makeToc([
  { id: 'ch-1', subchapters: [{ id: 'sub-1' }, { id: 'sub-2' }, { id: 'sub-3' }] },
]);

describe('useTocSync', () => {
  let onTocChanged: jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
    onTocChanged = jest.fn();
    mockGetToc.mockResolvedValue(SIMPLE_TOC);
  });

  // =====================================================================
  // tocUpdated event listener
  // =====================================================================

  describe('tocUpdated event listener', () => {
    it('calls onTocChanged when tocUpdated event fires with matching bookId', () => {
      renderHook(() => useTocSync({ bookId: BOOK_ID, onTocChanged }));

      act(() => {
        window.dispatchEvent(new CustomEvent('tocUpdated', { detail: { bookId: BOOK_ID } }));
      });

      expect(onTocChanged).toHaveBeenCalledTimes(1);
    });

    it('does not call onTocChanged when bookId does not match', () => {
      renderHook(() => useTocSync({ bookId: BOOK_ID, onTocChanged }));

      act(() => {
        window.dispatchEvent(new CustomEvent('tocUpdated', { detail: { bookId: OTHER_BOOK_ID } }));
      });

      expect(onTocChanged).not.toHaveBeenCalled();
    });

    it('calls onTocChanged once per event dispatch', () => {
      renderHook(() => useTocSync({ bookId: BOOK_ID, onTocChanged }));

      act(() => {
        window.dispatchEvent(new CustomEvent('tocUpdated', { detail: { bookId: BOOK_ID } }));
        window.dispatchEvent(new CustomEvent('tocUpdated', { detail: { bookId: BOOK_ID } }));
      });

      expect(onTocChanged).toHaveBeenCalledTimes(2);
    });

    it('removes the tocUpdated listener on unmount', () => {
      const removeSpy = jest.spyOn(window, 'removeEventListener');
      const { unmount } = renderHook(() => useTocSync({ bookId: BOOK_ID, onTocChanged }));

      unmount();

      expect(removeSpy).toHaveBeenCalledWith('tocUpdated', expect.any(Function));
      removeSpy.mockRestore();
    });

    it('no longer calls onTocChanged after unmount', () => {
      const { unmount } = renderHook(() => useTocSync({ bookId: BOOK_ID, onTocChanged }));
      unmount();

      act(() => {
        window.dispatchEvent(new CustomEvent('tocUpdated', { detail: { bookId: BOOK_ID } }));
      });

      expect(onTocChanged).not.toHaveBeenCalled();
    });
  });

  // =====================================================================
  // storage event listener
  // =====================================================================

  describe('storage event listener', () => {
    it('calls onTocChanged when storage event has the matching key and non-null value', () => {
      renderHook(() => useTocSync({ bookId: BOOK_ID, onTocChanged }));

      act(() => {
        window.dispatchEvent(
          new StorageEvent('storage', { key: `toc-updated-${BOOK_ID}`, newValue: '1234567890' }),
        );
      });

      expect(onTocChanged).toHaveBeenCalledTimes(1);
    });

    it('removes the localStorage flag after handling the storage event', () => {
      // Pre-populate the flag so we can verify it gets cleared
      localStorage.setItem(`toc-updated-${BOOK_ID}`, '1234567890');
      renderHook(() => useTocSync({ bookId: BOOK_ID, onTocChanged }));

      act(() => {
        window.dispatchEvent(
          new StorageEvent('storage', { key: `toc-updated-${BOOK_ID}`, newValue: '1234567890' }),
        );
      });

      expect(localStorage.getItem(`toc-updated-${BOOK_ID}`)).toBeNull();
    });

    it('does not call onTocChanged when the storage key does not match', () => {
      renderHook(() => useTocSync({ bookId: BOOK_ID, onTocChanged }));

      act(() => {
        window.dispatchEvent(
          new StorageEvent('storage', { key: `toc-updated-${OTHER_BOOK_ID}`, newValue: '1234567890' }),
        );
      });

      expect(onTocChanged).not.toHaveBeenCalled();
    });

    it('does not call onTocChanged when newValue is null', () => {
      renderHook(() => useTocSync({ bookId: BOOK_ID, onTocChanged }));

      act(() => {
        window.dispatchEvent(
          new StorageEvent('storage', { key: `toc-updated-${BOOK_ID}`, newValue: null }),
        );
      });

      expect(onTocChanged).not.toHaveBeenCalled();
    });

    it('does not call onTocChanged for storage events with unrelated keys', () => {
      renderHook(() => useTocSync({ bookId: BOOK_ID, onTocChanged }));

      act(() => {
        window.dispatchEvent(
          new StorageEvent('storage', { key: 'some-other-key', newValue: 'value' }),
        );
      });

      expect(onTocChanged).not.toHaveBeenCalled();
    });

    it('removes the storage listener on unmount', () => {
      const removeSpy = jest.spyOn(window, 'removeEventListener');
      const { unmount } = renderHook(() => useTocSync({ bookId: BOOK_ID, onTocChanged }));

      unmount();

      expect(removeSpy).toHaveBeenCalledWith('storage', expect.any(Function));
      removeSpy.mockRestore();
    });

    it('no longer calls onTocChanged for storage events after unmount', () => {
      const { unmount } = renderHook(() => useTocSync({ bookId: BOOK_ID, onTocChanged }));
      unmount();

      act(() => {
        window.dispatchEvent(
          new StorageEvent('storage', { key: `toc-updated-${BOOK_ID}`, newValue: '12345' }),
        );
      });

      expect(onTocChanged).not.toHaveBeenCalled();
    });
  });

  // =====================================================================
  // Polling (pollInterval > 0)
  // =====================================================================

  describe('polling', () => {
    const POLL_INTERVAL = 1000;

    beforeEach(() => {
      jest.useFakeTimers();
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    it('does not call getToc when pollInterval is 0 (default)', async () => {
      renderHook(() => useTocSync({ bookId: BOOK_ID, onTocChanged }));
      await flushPromises();

      jest.advanceTimersByTime(60000);
      await flushPromises();

      expect(mockGetToc).not.toHaveBeenCalled();
      expect(onTocChanged).not.toHaveBeenCalled();
    });

    it('calls getToc on initialization when pollInterval > 0', async () => {
      renderHook(() => useTocSync({ bookId: BOOK_ID, onTocChanged, pollInterval: POLL_INTERVAL }));
      await flushPromises();

      expect(mockGetToc).toHaveBeenCalledWith(BOOK_ID);
      expect(mockGetToc).toHaveBeenCalledTimes(1);
    });

    it('does not call onTocChanged on initialization (only sets initial hash)', async () => {
      renderHook(() => useTocSync({ bookId: BOOK_ID, onTocChanged, pollInterval: POLL_INTERVAL }));
      await flushPromises();

      expect(onTocChanged).not.toHaveBeenCalled();
    });

    it('does not call onTocChanged when TOC hash remains the same between polls', async () => {
      mockGetToc.mockResolvedValue(SIMPLE_TOC); // same on all calls

      renderHook(() => useTocSync({ bookId: BOOK_ID, onTocChanged, pollInterval: POLL_INTERVAL }));
      await flushPromises();

      await act(async () => {
        jest.advanceTimersByTime(POLL_INTERVAL);
        await Promise.resolve();
        await Promise.resolve();
        await Promise.resolve();
      });

      expect(onTocChanged).not.toHaveBeenCalled();
    });

    it('calls onTocChanged when TOC hash changes between polls (new chapter added)', async () => {
      mockGetToc
        .mockResolvedValueOnce(SIMPLE_TOC)    // initial hash
        .mockResolvedValueOnce(MODIFIED_TOC); // first poll — different

      renderHook(() => useTocSync({ bookId: BOOK_ID, onTocChanged, pollInterval: POLL_INTERVAL }));
      await flushPromises();

      await act(async () => {
        jest.advanceTimersByTime(POLL_INTERVAL);
        await Promise.resolve();
        await Promise.resolve();
        await Promise.resolve();
      });

      expect(onTocChanged).toHaveBeenCalledTimes(1);
    });

    it('detects hash changes when only subchapters differ', async () => {
      mockGetToc
        .mockResolvedValueOnce(TOC_WITH_SUBCHAPTERS)
        .mockResolvedValueOnce(TOC_MODIFIED_SUBCHAPTERS);

      renderHook(() => useTocSync({ bookId: BOOK_ID, onTocChanged, pollInterval: POLL_INTERVAL }));
      await flushPromises();

      await act(async () => {
        jest.advanceTimersByTime(POLL_INTERVAL);
        await Promise.resolve();
        await Promise.resolve();
        await Promise.resolve();
      });

      expect(onTocChanged).toHaveBeenCalledTimes(1);
    });

    it('does not call onTocChanged when getToc returns null toc on init', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      mockGetToc.mockResolvedValue({ toc: null });

      renderHook(() => useTocSync({ bookId: BOOK_ID, onTocChanged, pollInterval: POLL_INTERVAL }));
      await flushPromises();

      await act(async () => {
        jest.advanceTimersByTime(POLL_INTERVAL);
        await Promise.resolve();
        await Promise.resolve();
        await Promise.resolve();
      });

      expect(onTocChanged).not.toHaveBeenCalled();
      consoleSpy.mockRestore();
    });

    it('does not call onTocChanged when getToc throws an error', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      mockGetToc.mockRejectedValue(new Error('Network error'));

      renderHook(() => useTocSync({ bookId: BOOK_ID, onTocChanged, pollInterval: POLL_INTERVAL }));
      await flushPromises();

      await act(async () => {
        jest.advanceTimersByTime(POLL_INTERVAL);
        await Promise.resolve();
        await Promise.resolve();
        await Promise.resolve();
      });

      expect(onTocChanged).not.toHaveBeenCalled();
      consoleSpy.mockRestore();
    });

    it('clears the poll timeout on unmount', async () => {
      const clearTimeoutSpy = jest.spyOn(global, 'clearTimeout');
      const { unmount } = renderHook(() =>
        useTocSync({ bookId: BOOK_ID, onTocChanged, pollInterval: POLL_INTERVAL }),
      );
      await flushPromises();

      unmount();

      expect(clearTimeoutSpy).toHaveBeenCalled();
      clearTimeoutSpy.mockRestore();
    });

    it('polls repeatedly at the given interval', async () => {
      mockGetToc.mockResolvedValue(SIMPLE_TOC);

      renderHook(() => useTocSync({ bookId: BOOK_ID, onTocChanged, pollInterval: POLL_INTERVAL }));
      await flushPromises();

      // Advance through two full poll cycles
      for (let i = 0; i < 2; i++) {
        await act(async () => {
          jest.advanceTimersByTime(POLL_INTERVAL);
          await Promise.resolve();
          await Promise.resolve();
          await Promise.resolve();
        });
      }

      // 1 init + 2 polls = 3 calls
      expect(mockGetToc).toHaveBeenCalledTimes(3);
    });
  });
});

// =====================================================================
// triggerTocUpdateEvent
// =====================================================================

describe('triggerTocUpdateEvent', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('dispatches a tocUpdated CustomEvent on window', () => {
    const dispatchSpy = jest.spyOn(window, 'dispatchEvent');

    triggerTocUpdateEvent(BOOK_ID);

    expect(dispatchSpy).toHaveBeenCalledTimes(1);
    const dispatched = dispatchSpy.mock.calls[0][0] as CustomEvent;
    expect(dispatched.type).toBe('tocUpdated');
    dispatchSpy.mockRestore();
  });

  it('includes the bookId in the event detail', () => {
    const dispatchSpy = jest.spyOn(window, 'dispatchEvent');

    triggerTocUpdateEvent(BOOK_ID);

    const dispatched = dispatchSpy.mock.calls[0][0] as CustomEvent;
    expect(dispatched.detail.bookId).toBe(BOOK_ID);
    dispatchSpy.mockRestore();
  });

  it('includes a numeric timestamp in the event detail', () => {
    const dispatchSpy = jest.spyOn(window, 'dispatchEvent');

    triggerTocUpdateEvent(BOOK_ID);

    const dispatched = dispatchSpy.mock.calls[0][0] as CustomEvent;
    expect(typeof dispatched.detail.timestamp).toBe('number');
    dispatchSpy.mockRestore();
  });

  it('sets a localStorage flag for cross-tab communication', () => {
    triggerTocUpdateEvent(BOOK_ID);

    expect(localStorage.getItem(`toc-updated-${BOOK_ID}`)).not.toBeNull();
  });

  it('stores a numeric string (timestamp) as the localStorage flag value', () => {
    triggerTocUpdateEvent(BOOK_ID);

    const storedValue = localStorage.getItem(`toc-updated-${BOOK_ID}`);
    expect(storedValue).not.toBeNull();
    expect(Number.isFinite(Number(storedValue))).toBe(true);
  });

  it('uses the bookId in the localStorage key', () => {
    const customBookId = 'my-custom-book-id';

    triggerTocUpdateEvent(customBookId);

    expect(localStorage.getItem(`toc-updated-${customBookId}`)).not.toBeNull();
  });

  it('a hook listening for the event is triggered when triggerTocUpdateEvent is called', () => {
    const onTocChanged = jest.fn();
    renderHook(() => useTocSync({ bookId: BOOK_ID, onTocChanged }));

    act(() => {
      triggerTocUpdateEvent(BOOK_ID);
    });

    expect(onTocChanged).toHaveBeenCalledTimes(1);
  });
});
