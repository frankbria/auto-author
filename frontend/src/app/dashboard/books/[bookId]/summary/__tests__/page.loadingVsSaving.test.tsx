import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

import BookSummaryPage from '../page';
import bookClient from '@/lib/api/bookClient';

jest.mock('@/lib/api/bookClient');
jest.mock('@/lib/voice/useSpeechRecognitionSupported', () => ({
  useSpeechRecognitionSupported: () => false,
}));

const mockPush = jest.fn();
let mockParams: Record<string, string> = { bookId: 'book-1' };
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
  useParams: () => mockParams,
}));

const mockedClient = bookClient as jest.Mocked<typeof bookClient>;

/**
 * Loading the summary and saving it are two different states (#584).
 *
 * They used to be one `isLoading` flag, written by both the fetch effect and the
 * submit handler, and read only by the submit button. So while the page was
 * *loading*, its button already said **"Saving..."** — before anything had been
 * saved. That is a live defect, not a latent one: the fetch sets the flag on
 * every mount.
 *
 * It also made the `set-state-in-effect` fix impossible on its own terms. The
 * obvious move — start the flag `true`, since the effect always fetches — would
 * have shown "Saving..." on the *first paint* as well, which is why it was
 * reverted rather than shipped, and why this split came first.
 *
 * The page had no test file, so these pin the distinction from the outside:
 * what the button says, and when.
 */

const READY_SUMMARY =
  'This book examines how small teams ship software under real constraints, ' +
  'drawing on field notes from a dozen engineering organisations, and argues ' +
  'that most delivery problems are organisational rather than technical in ' +
  'their origin and in their eventual resolution.';

const submitButton = () => screen.getByRole('button', { name: /Continue to TOC Generation|Saving/ });

describe('BookSummaryPage: loading is not saving (#584)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockParams = { bookId: 'book-1' };
  });

  it('does not say "Saving..." while it is loading', async () => {
    // The headline defect. One flag meant the fetch announced itself with the
    // save's label.
    let resolveFetch: (value: { summary: string; summary_history?: unknown[] }) => void = () => {};
    mockedClient.getBookSummary.mockReturnValue(
      new Promise<{ summary: string; summary_history?: unknown[] }>((resolve) => {
        resolveFetch = resolve;
      })
    );

    render(<BookSummaryPage />);

    expect(submitButton()).toHaveTextContent('Continue to TOC Generation');
    expect(submitButton()).not.toHaveTextContent('Saving');
    // Still disabled, though: there is nothing loaded to submit yet.
    expect(submitButton()).toBeDisabled();
    expect(submitButton()).not.toHaveAttribute('aria-busy');

    resolveFetch({ summary: READY_SUMMARY, summary_history: [] });
    await waitFor(() => expect(submitButton()).toBeEnabled());
  });

  it('says "Saving..." only once a save is actually running', async () => {
    mockedClient.getBookSummary.mockResolvedValue({ summary: READY_SUMMARY, summary_history: [] });
    let resolveSave: (value: { summary: string; success: boolean }) => void = () => {};
    mockedClient.saveBookSummary.mockReturnValue(
      new Promise<{ summary: string; success: boolean }>((resolve) => {
        resolveSave = resolve;
      })
    );

    render(<BookSummaryPage />);
    await waitFor(() => expect(submitButton()).toBeEnabled());

    await userEvent.click(submitButton());

    await waitFor(() => expect(submitButton()).toHaveTextContent('Saving...'));
    expect(submitButton()).toHaveAttribute('aria-busy', 'true');

    resolveSave({ summary: READY_SUMMARY, success: true });
    await waitFor(() => expect(mockPush).toHaveBeenCalled());
  });

  it('is not stuck loading when there is no book to load', async () => {
    // `isLoadingSummary` is derived rather than stored precisely so this case
    // needs no effect to announce it. A stored flag initialised to `true` would
    // leave the button disabled forever here.
    mockParams = {};

    render(<BookSummaryPage />);

    expect(mockedClient.getBookSummary).not.toHaveBeenCalled();
    expect(submitButton()).toHaveTextContent('Continue to TOC Generation');
    // Disabled for the ordinary reason — an empty summary — not for loading.
    expect(submitButton()).toBeDisabled();

    // The discriminating half. "Disabled" alone cannot tell the two reasons
    // apart, so a stored `!summaryLoaded` passed this test until typing a ready
    // summary was added: under that version the button stays disabled forever,
    // waiting for a fetch that never runs.
    await userEvent.click(screen.getByPlaceholderText(/Describe your book/i));
    await userEvent.paste(READY_SUMMARY);

    await waitFor(() => expect(submitButton()).toBeEnabled());
  });

  it('shows the loading state again when the book changes', async () => {
    // The app router keeps this component mounted across a `[bookId]` change, so
    // the cleanup has to re-arm the state or the next book renders the previous
    // one's summary as though it had loaded.
    mockedClient.getBookSummary.mockResolvedValue({ summary: READY_SUMMARY, summary_history: [] });
    const { rerender } = render(<BookSummaryPage />);
    await waitFor(() => expect(submitButton()).toBeEnabled());

    let resolveSecond: (value: { summary: string; summary_history?: unknown[] }) => void = () => {};
    mockedClient.getBookSummary.mockReturnValue(
      new Promise<{ summary: string; summary_history?: unknown[] }>((resolve) => {
        resolveSecond = resolve;
      })
    );
    mockParams = { bookId: 'book-2' };
    rerender(<BookSummaryPage />);

    await waitFor(() => expect(submitButton()).toBeDisabled());
    expect(submitButton()).toHaveTextContent('Continue to TOC Generation');

    resolveSecond({ summary: READY_SUMMARY, summary_history: [] });
    await waitFor(() => expect(submitButton()).toBeEnabled());
  });
});
