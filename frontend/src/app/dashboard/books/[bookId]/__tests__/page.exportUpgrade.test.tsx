import React, { Suspense } from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import BookPage from '../page';
import { useSession } from '@/lib/auth-client';
import bookClient from '@/lib/api/bookClient';
import { showErrorNotification } from '@/components/errors';

// Export is part of Pro; the free trial is one chapter (owner decision
// 2026-10-28). A 402 from an export must say why and offer the upgrade, not a
// retry that would be refused again.

jest.mock('@/lib/auth-client');
jest.mock('@/lib/api/bookClient');
jest.mock('@/lib/toast', () => ({
  toast: Object.assign(jest.fn(), {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
  }),
}));
jest.mock('@/components/errors', () => ({
  showErrorNotification: jest.fn(),
  showRecoveryNotification: jest.fn(),
}));
// The options modal is not what this suite tests: stand it in with one button
// that asks for an EPUB.
jest.mock('@/components/export/ExportOptionsModal', () => ({
  ExportOptionsModal: ({
    isOpen,
    onExport,
  }: {
    isOpen: boolean;
    onExport: (o: { format: string; includeEmptyChapters: boolean }) => void;
  }) =>
    isOpen ? (
      <button onClick={() => onExport({ format: 'epub', includeEmptyChapters: false })}>
        Start EPUB export
      </button>
    ) : null,
}));

const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;

function fulfilledParams<T>(value: T): Promise<T> {
  const p = Promise.resolve(value) as Promise<T> & { status: string; value: T };
  p.status = 'fulfilled';
  p.value = value;
  return p;
}

function renderPage() {
  return render(
    <Suspense fallback={null}>
      <BookPage params={fulfilledParams({ bookId: 'book-1' })} />
    </Suspense>
  );
}

function failure(status: number, message: string) {
  return Object.assign(new Error(message), { statusCode: status, userMessage: message });
}

describe('BookPage export refused by the plan', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useSession as jest.Mock).mockReturnValue({ data: { user: { id: 'u1' } } });
    mockBookClient.getChaptersMetadata.mockResolvedValue({ chapters: [] } as never);
    mockBookClient.getBookSummary.mockResolvedValue({ summary: '' } as never);
    mockBookClient.getBook.mockResolvedValue({
      id: 'book-1',
      title: 'My Nonfiction Book',
      description: 'desc',
      progress: 0,
    } as never);
  });

  it('shows the reason and an upgrade link, with no retry', async () => {
    const reason = 'Exporting your book is part of Pro.';
    mockBookClient.exportEPUB.mockRejectedValue(failure(402, reason));

    renderPage();
    fireEvent.click((await screen.findAllByRole('button', { name: /export book/i }))[0]);
    fireEvent.click(await screen.findByRole('button', { name: 'Start EPUB export' }));

    expect(await screen.findByRole('link', { name: 'Upgrade to Pro' })).toHaveAttribute(
      'href',
      '/dashboard/settings?tab=billing'
    );
    expect(screen.getByText(reason)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Retry Export' })).not.toBeInTheDocument();
    expect(mockBookClient.exportEPUB).toHaveBeenCalledTimes(1);
    expect(showErrorNotification).not.toHaveBeenCalled();
  });

  it('keeps the retry for a failure that is not about the plan', async () => {
    mockBookClient.exportEPUB.mockRejectedValue(failure(400, 'This book has no chapter content yet.'));

    renderPage();
    fireEvent.click((await screen.findAllByRole('button', { name: /export book/i }))[0]);
    fireEvent.click(await screen.findByRole('button', { name: 'Start EPUB export' }));

    expect(await screen.findByRole('button', { name: 'Retry Export' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Upgrade to Pro' })).not.toBeInTheDocument();
    expect(showErrorNotification).toHaveBeenCalled();
  });
});
