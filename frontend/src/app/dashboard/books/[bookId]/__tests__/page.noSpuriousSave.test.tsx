import React, { Suspense } from 'react';
import { render, screen } from '@testing-library/react';
import BookPage from '../page';
import { useSession } from '@/lib/auth-client';
import bookClient from '@/lib/api/bookClient';
import { toast } from '@/lib/toast';

/**
 * #350: opening a book must not write to the server or claim it saved.
 *
 * The page held a `useForm` whose only consumers were a reset-on-load effect and
 * an un-debounced `watch()` auto-save — no input on the page was ever bound to
 * it. Editing is owned by BookMetadataForm, which has its own form and save
 * handler; the page-level one could only ever fire writes nobody asked for.
 *
 * Honest scope of these tests: they pin the invariant (loading a book performs
 * no write and claims no save), NOT a reproduction of the original report. On
 * `main` this suite passes too, because the reset effect is declared before the
 * watch effect, so on the load path the subscription is recreated *after* the
 * reset that would have notified it. The reported toast needs a sequence where
 * `book` changes while the subscription is already live. These therefore guard
 * against reintroduction rather than prove a reproduced fix — see the PR for why
 * the code was removed regardless.
 */

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

const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;

// React's use(params) can't suspend-then-resume on a plain resolved Promise in
// jest; a pre-fulfilled thenable lets it read the value synchronously (#194).
function fulfilledParams<T>(value: T): Promise<T> {
  const p = Promise.resolve(value) as Promise<T> & { status: string; value: T };
  p.status = 'fulfilled';
  p.value = value;
  return p;
}

// Shape mirrors the fixture in page.errorRetry.test.tsx, which is known to
// render this page cleanly.
const BOOK = {
  id: 'book-1',
  title: 'A Test Book',
  description: 'desc',
  progress: 0,
};

function renderPage() {
  return render(
    <Suspense fallback={null}>
      <BookPage params={fulfilledParams({ bookId: 'book-1' })} />
    </Suspense>
  );
}

describe('BookPage load does not auto-save (#350)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useSession as jest.Mock).mockReturnValue({ data: { user: { id: 'u1' } } });
    mockBookClient.getBook.mockResolvedValue(BOOK as never);
    mockBookClient.getToc.mockResolvedValue({ toc: null } as never);
    mockBookClient.getBookSummary.mockResolvedValue({ summary: '' } as never);
    mockBookClient.updateBook.mockResolvedValue(BOOK as never);
  });

  it('does not PATCH the book just because it was opened', async () => {
    renderPage();

    await screen.findByRole('heading', { level: 1, name: BOOK.title });
    // Give any stray watch/reset subscription a chance to fire.
    await new Promise((r) => setTimeout(r, 50));

    expect(mockBookClient.updateBook).not.toHaveBeenCalled();
  });

  it('does not claim the book was saved on load', async () => {
    renderPage();

    await screen.findByRole('heading', { level: 1, name: BOOK.title });
    await new Promise((r) => setTimeout(r, 50));

    // A success toast for something the user never did is worse than silence:
    // it teaches them the toast carries no information.
    expect(toast.success).not.toHaveBeenCalled();
  });
});
