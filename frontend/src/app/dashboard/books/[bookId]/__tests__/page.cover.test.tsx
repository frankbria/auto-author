import React, { Suspense } from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

import BookPage from '../page';
import bookClient from '@/lib/api/bookClient';

jest.mock('next/navigation', () => {
  const params = new URLSearchParams();
  return { useSearchParams: () => params };
});
jest.mock('@/lib/api/bookClient', () => ({
  __esModule: true,
  default: {
    getBook: jest.fn(),
    getChaptersMetadata: jest.fn(),
    getBookSummary: jest.fn(),
  },
}));
jest.mock('@/lib/toast', () => ({ toast: Object.assign(jest.fn(), { error: jest.fn(), success: jest.fn() }) }));
jest.mock('@/components/navigation/ChapterBreadcrumb', () => ({ ChapterBreadcrumb: () => null }));
jest.mock('@/components/BookMetadataForm', () => ({ BookMetadataForm: () => null }));
jest.mock('@/components/chapters/ChapterTabs', () => ({ ChapterTabs: () => null }));
jest.mock('@/components/export/ExportOptionsModal', () => ({ ExportOptionsModal: () => null }));
jest.mock('@/components/export/ExportProgressModal', () => ({ ExportProgressModal: () => null }));

/**
 * A stored cover renders on the book page, and the edit view can upload one (#941).
 * A local-storage URL is relative to the API, not to this page.
 */

const mockedClient = bookClient as jest.Mocked<typeof bookClient>;
type Book = Awaited<ReturnType<typeof bookClient.getBook>>;

const value = { bookId: 'book-1' };
const params = Object.assign(Promise.resolve(value), { status: 'fulfilled', value }) as Promise<{ bookId: string }>;

function theBook(fields: Record<string, unknown>) {
  mockedClient.getBook.mockResolvedValue(
    { id: 'book-1', title: 'Covered', description: '', owner_id: 'u1', created_at: '', updated_at: '', ...fields } as unknown as Book,
  );
}

const renderPage = () =>
  render(
    <Suspense fallback={null}>
      <BookPage params={params} />
    </Suspense>,
  );

beforeEach(() => {
  jest.clearAllMocks();
  mockedClient.getChaptersMetadata.mockRejectedValue(new Error('none'));
  mockedClient.getBookSummary.mockResolvedValue({ summary: '' } as never);
});

it('renders a local cover from the API origin', async () => {
  theBook({ cover_image_url: '/uploads/cover_images/book-1_c.jpg' });
  renderPage();
  const img = await screen.findByRole('img', { name: /book cover/i });
  expect(img).toHaveAttribute('src', 'http://localhost:8000/uploads/cover_images/book-1_c.jpg');
});

it('renders a cloud cover as it is, without the image optimizer', async () => {
  const url = 'https://bkt.s3.us-east-1.amazonaws.com/cover_images/book-1/c.jpg';
  theBook({ cover_image_url: url });
  renderPage();
  expect(await screen.findByRole('img', { name: /book cover/i })).toHaveAttribute('src', url);
});

it('the edit view has a cover upload control', async () => {
  theBook({});
  renderPage();
  fireEvent.click(await screen.findByRole('button', { name: /edit book/i }));
  expect(screen.getByLabelText(/upload book cover/i)).toHaveAttribute('type', 'file');
  expect(screen.getByRole('button', { name: /upload cover/i })).toBeInTheDocument();
});
