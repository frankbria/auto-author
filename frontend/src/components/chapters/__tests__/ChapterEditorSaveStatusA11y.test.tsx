/**
 * #349: an autosave failure must be announced, and must not be reported as a
 * success.
 *
 * `lastSaved` survives from the previous successful save, so the footer kept
 * rendering "Saved 14:32" while the save was failing. Once that footer became a
 * polite live region, it announced a stale success — and the failure message
 * itself had no `role="alert"`, so the actual outcome was announced nowhere.
 * A screen-reader user was told the opposite of what happened.
 */
import { render, screen, act, waitFor } from '@testing-library/react';
import { ChapterEditor } from '@/components/chapters/ChapterEditor';
import bookClient from '@/lib/api/bookClient';

jest.mock('@/lib/api/bookClient', () => ({
  __esModule: true,
  default: {
    getChapterContent: jest.fn(),
    saveChapterContent: jest.fn(),
  },
}));

const mockClient = bookClient as unknown as {
  getChapterContent: jest.Mock;
  saveChapterContent: jest.Mock;
};

describe('ChapterEditor save status announcements (#349)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockClient.getChapterContent.mockResolvedValue({ content: '<p>hi</p>' });
  });

  it('announces a save failure through an alert', async () => {
    mockClient.saveChapterContent.mockRejectedValue(new Error('network down'));

    await act(async () => {
      render(<ChapterEditor bookId="b1" chapterId="c1" chapterTitle="Ch" />);
    });

    await act(async () => {
      screen.getByRole('button', { name: /^save$/i }).click();
    });

    await waitFor(() => {
      // Assertive, because the writing may now exist only in the local backup.
      expect(screen.getByRole('alert')).toHaveTextContent(/failed to save/i);
    });
  });

  it('does not keep reporting the previous success while a save is failing', async () => {
    mockClient.saveChapterContent
      .mockResolvedValueOnce({})
      .mockRejectedValueOnce(new Error('network down'));

    await act(async () => {
      render(<ChapterEditor bookId="b1" chapterId="c1" chapterTitle="Ch" />);
    });

    const save = screen.getByRole('button', { name: /^save$/i });

    // First save succeeds, so lastSaved is populated.
    await act(async () => {
      save.click();
    });
    await waitFor(() => {
      expect(screen.getByTestId('save-status-indicator')).toHaveAttribute(
        'data-save-status',
        'saved'
      );
    });

    // Second save fails. The status region must not still say "Saved <time>".
    await act(async () => {
      save.click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('save-status-indicator')).toHaveAttribute(
        'data-save-status',
        'error'
      );
    });
    expect(screen.getByTestId('save-status-indicator')).not.toHaveTextContent(/^Saved /);
  });
});
