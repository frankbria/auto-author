import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

import { ExportOptionsModal } from '../ExportOptionsModal';
import type { UserPreferences } from '@/hooks/useProfileApi';

jest.mock('@/hooks/usePerformanceTracking', () => ({
  usePerformanceTracking: () => ({
    trackOperation: async (_name: string, fn: () => unknown) => fn(),
  }),
}));
jest.mock('sonner', () => ({ toast: { error: jest.fn(), success: jest.fn() } }));
jest.mock('@/lib/api/bookClient', () => ({
  __esModule: true,
  default: {
    getExportFormats: jest.fn(() =>
      Promise.resolve({
        data: {
          book_stats: {
            total_chapters: 10,
            chapters_with_content: 8,
            total_word_count: 50000,
            estimated_pages: 200,
          },
        },
      })
    ),
  },
}));

// `mock`-prefixed so the hoisted `jest.mock` factory below may close over it.
// This repo transforms with SWC, which does not enforce that — the file passes
// without it — but babel-plugin-jest-hoist does, so the prefix keeps it
// portable, matching `mockPush`/`mockParams` elsewhere.
let mockPreferences: UserPreferences | null = null;
jest.mock('@/hooks/useUserPreferences', () => ({
  __esModule: true,
  useUserPreferences: () => mockPreferences,
  invalidateUserPreferencesCache: jest.fn(),
}));

/**
 * Stored export defaults, and when they may overwrite a choice (#693).
 *
 * `optionsTouchedRef` used to guard *every* preference arrival. It is never
 * reset, and this component never unmounts — `books/[bookId]/page.tsx` renders
 * it unconditionally rather than behind `{showExportModal && …}` — so a single
 * touch disabled the stored defaults for the life of the page. Changing the
 * default export format in Settings then did nothing until a reload.
 *
 * That became reachable with #674, which gave `useUserPreferences` real
 * subscribers, so a save now notifies mounted consumers instead of being seen
 * only by the next component to mount.
 *
 * It now guards the **first** arrival only: preferences load asynchronously, so
 * a format picked in the moment before they land must not be overwritten. A
 * later change can only come from the user deliberately saving new preferences,
 * and that wins.
 */

const props = {
  isOpen: true,
  bookId: 'book-1',
  bookTitle: 'A Book',
  onOpenChange: jest.fn(),
  onExport: jest.fn(),
};

const prefs = (format: string): UserPreferences =>
  ({ default_export_format: format } as unknown as UserPreferences);

/** The value the format radio group currently shows as selected. */
function selectedFormat(): string | undefined {
  return screen
    .getAllByRole('radio')
    .find((radio) => radio.getAttribute('aria-checked') === 'true' || radio.getAttribute('data-state') === 'checked')
    ?.getAttribute('value') ?? undefined;
}

describe('ExportOptionsModal stored defaults (#693)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockPreferences = null;
  });

  it('applies the stored default when preferences arrive', async () => {
    const { rerender } = render(<ExportOptionsModal {...props} />);
    expect(selectedFormat()).toBe('pdf');

    mockPreferences = prefs('epub');
    rerender(<ExportOptionsModal {...props} />);

    expect(selectedFormat()).toBe('epub');
  });

  it('does not overwrite a choice made before preferences land', async () => {
    // The case `optionsTouchedRef` exists for, and the reason it cannot simply
    // be deleted.
    const { rerender } = render(<ExportOptionsModal {...props} />);

    await userEvent.click(screen.getByLabelText(/Word Document/i));
    expect(selectedFormat()).toBe('docx');

    mockPreferences = prefs('epub');
    rerender(<ExportOptionsModal {...props} />);

    expect(selectedFormat()).toBe('docx');
  });

  it('applies a later change even after the format has been touched', async () => {
    // The defect. Saving a new default in Settings notifies this consumer; the
    // old guard made it a no-op for the life of the page.
    mockPreferences = prefs('pdf');
    const { rerender } = render(<ExportOptionsModal {...props} />);
    expect(selectedFormat()).toBe('pdf');

    await userEvent.click(screen.getByLabelText(/Word Document/i));
    expect(selectedFormat()).toBe('docx');

    mockPreferences = prefs('epub');
    rerender(<ExportOptionsModal {...props} />);

    expect(selectedFormat()).toBe('epub');
  });

  it('leaves the choice alone when the preferences object is unchanged', async () => {
    // Re-rendering for any other reason must not undo a choice — the guard on
    // object identity, not just on "did anything arrive".
    mockPreferences = prefs('pdf');
    const { rerender } = render(<ExportOptionsModal {...props} />);

    await userEvent.click(screen.getByLabelText(/Word Document/i));
    expect(selectedFormat()).toBe('docx');

    rerender(<ExportOptionsModal {...props} bookTitle="A Book, renamed" />);

    expect(selectedFormat()).toBe('docx');
  });
});
