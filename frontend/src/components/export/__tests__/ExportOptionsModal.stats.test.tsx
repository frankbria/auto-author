import React from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import { ExportOptionsModal } from '../ExportOptionsModal';

// One function for the module, as the real hook's useCallback([]) provides.
// A fresh one per render would re-run every effect that depends on it.
jest.mock('@/hooks/usePerformanceTracking', () => {
  const trackOperation = async (_name: string, fn: () => unknown) => fn();
  return { usePerformanceTracking: () => ({ trackOperation }) };
});
jest.mock('sonner', () => ({ toast: { error: jest.fn(), success: jest.fn() } }));
jest.mock('@/hooks/useUserPreferences', () => ({
  __esModule: true,
  useUserPreferences: () => null,
  invalidateUserPreferencesCache: jest.fn(),
}));

type Formats = { data: { book_stats: Record<string, number>; templates?: unknown[] } };
const mockGetExportFormats = jest.fn<Promise<Formats>, [string]>();
jest.mock('@/lib/api/bookClient', () => ({
  __esModule: true,
  default: { getExportFormats: (bookId: string) => mockGetExportFormats(bookId) },
}));

/**
 * Book statistics load each time the modal opens (#584).
 *
 * While a request for *this* open is in flight, the statistics panel is hidden
 * and Export is disabled; when it settles, either way, Export comes back. These
 * were written against the effect that set a loading flag synchronously, and
 * they are what its replacement has to keep.
 */

const formats = (chapters: number): Formats => ({
  data: {
    book_stats: {
      total_chapters: chapters,
      chapters_with_content: 5,
      total_word_count: 1000,
      estimated_pages: 4,
    },
  },
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

const props = {
  bookId: 'book-1',
  bookTitle: 'A Book',
  onOpenChange: jest.fn(),
  onExport: jest.fn(),
};

const exportButton = () => screen.getByRole('button', { name: /^export /i });

describe('ExportOptionsModal book statistics (#584)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('hides the statistics and disables Export until the request settles', async () => {
    const request = deferred<Formats>();
    mockGetExportFormats.mockReturnValueOnce(request.promise);

    render(<ExportOptionsModal {...props} isOpen />);

    await waitFor(() => expect(exportButton()).toBeDisabled());
    expect(screen.queryByText('Total Chapters:')).not.toBeInTheDocument();

    request.resolve(formats(7));

    await waitFor(() => expect(exportButton()).toBeEnabled());
    expect(screen.getByText('Total Chapters:')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
  });

  it('re-enables Export when the request fails', async () => {
    mockGetExportFormats.mockRejectedValueOnce(new Error('offline'));

    render(<ExportOptionsModal {...props} isOpen />);

    await waitFor(() => expect(exportButton()).toBeEnabled());
    expect(screen.queryByText('Total Chapters:')).not.toBeInTheDocument();
  });

  it('refetches on every open, and waits for that open’s response', async () => {
    mockGetExportFormats.mockResolvedValueOnce(formats(7));
    const { rerender } = render(<ExportOptionsModal {...props} isOpen />);
    await waitFor(() => expect(screen.getByText('7')).toBeInTheDocument());

    const second = deferred<Formats>();
    mockGetExportFormats.mockReturnValueOnce(second.promise);
    rerender(<ExportOptionsModal {...props} isOpen={false} />);
    rerender(<ExportOptionsModal {...props} isOpen />);

    await waitFor(() => expect(exportButton()).toBeDisabled());
    expect(mockGetExportFormats).toHaveBeenCalledTimes(2);

    second.resolve(formats(9));
    await waitFor(() => expect(screen.getByText('9')).toBeInTheDocument());
    expect(exportButton()).toBeEnabled();
  });

  it('ignores a late response from an earlier open', async () => {
    // Close before the first request settles, reopen, then let the *first*
    // response land. It belongs to an open the user already dismissed, so it must
    // neither show its figures nor enable Export while the current request is
    // still running.
    const first = deferred<Formats>();
    const second = deferred<Formats>();
    mockGetExportFormats.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);

    const { rerender } = render(<ExportOptionsModal {...props} isOpen />);
    await waitFor(() => expect(exportButton()).toBeDisabled());
    rerender(<ExportOptionsModal {...props} isOpen={false} />);
    rerender(<ExportOptionsModal {...props} isOpen />);
    await waitFor(() => expect(mockGetExportFormats).toHaveBeenCalledTimes(2));

    // Inside act, so the stale response's continuation and any render it causes
    // are flushed before asserting that it changed nothing. A bare timeout here
    // left the render pending and passed against the racy version.
    await act(async () => {
      first.resolve(formats(7));
    });
    expect(exportButton()).toBeDisabled();
    expect(screen.queryByText('7')).not.toBeInTheDocument();

    second.resolve(formats(9));
    await waitFor(() => expect(screen.getByText('9')).toBeInTheDocument());
    expect(exportButton()).toBeEnabled();
  });
});
