import React, { Suspense } from 'react';
import { render, screen, within } from '@testing-library/react';
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
    getToc: jest.fn(),
    getChaptersMetadata: jest.fn(),
    getBookSummary: jest.fn(),
  },
}));
jest.mock('@/lib/toast', () => ({ toast: Object.assign(jest.fn(), { error: jest.fn(), success: jest.fn() }) }));
jest.mock('@/components/navigation/ChapterBreadcrumb', () => ({ ChapterBreadcrumb: () => null }));
jest.mock('@/components/BookMetadataForm', () => ({ BookMetadataForm: () => null }));
jest.mock('@/components/chapters/ChapterTabs', () => ({ ChapterTabs: () => <div data-testid="chapter-tabs" /> }));
jest.mock('@/components/export/ExportOptionsModal', () => ({ ExportOptionsModal: () => null }));
jest.mock('@/components/export/ExportProgressModal', () => ({ ExportProgressModal: () => null }));

/**
 * The Book Stats panel shows the book's numbers (#833).
 *
 * It showed a word count of 0 and "0 of N" chapters completed for every book,
 * because both were written into the page as constants, and a progress of
 * "undefined%", because it read a field the book route does not return. The
 * same invention was taken out of the book cards in #291.
 */

const mockedClient = bookClient as jest.Mocked<typeof bookClient>;
type Book = Awaited<ReturnType<typeof bookClient.getBook>>;
type Metadata = Awaited<ReturnType<typeof bookClient.getChaptersMetadata>>;

const value = { bookId: 'book-1' };
const params = Object.assign(Promise.resolve(value), { status: 'fulfilled', value }) as Promise<{ bookId: string }>;

const chapter = (id: string, status: string, word_count: number) => ({
  id, title: `Chapter ${id}`, description: '', level: 1, order: 1, status, word_count,
  estimated_reading_time: 1, last_modified: '2026-10-01T00:00:00Z',
});

function theBookHas(chapters: ReturnType<typeof chapter>[]) {
  mockedClient.getChaptersMetadata.mockResolvedValue({
    book_id: 'book-1', chapters, total_chapters: chapters.length,
    completion_stats: { draft: 0, in_progress: 0, completed: 0, published: 0 },
  } as Metadata);
}

async function stats() {
  render(
    <Suspense fallback={null}>
      <BookPage params={params} />
    </Suspense>,
  );
  const heading = await screen.findByRole('heading', { name: 'Book Stats' });
  return within(heading.parentElement as HTMLElement);
}

beforeEach(() => {
  jest.clearAllMocks();
  mockedClient.getBook.mockResolvedValue(
    { id: 'book-1', title: 'The Lighthouse Letters', description: '', owner_id: 'u1', created_at: '', updated_at: '' } as unknown as Book,
  );
  mockedClient.getBookSummary.mockResolvedValue({ summary: 'A summary long enough to count as one.', summary_history: [] } as never);
  mockedClient.getToc.mockRejectedValue(new Error('the page should not need the table of contents for its stats'));
});

describe('the Book Stats panel', () => {
  it('shows the progress, the words and the completed chapters the book has', async () => {
    theBookHas([
      chapter('c1', 'completed', 1200),
      chapter('c2', 'published', 800),
      chapter('c3', 'in-progress', 350),
      chapter('c4', 'draft', 0),
    ]);

    const panel = await stats();

    expect(panel.getByText('50%')).toBeInTheDocument();
    expect(panel.getByText('2,350')).toBeInTheDocument();
    expect(panel.getByText('2 of 4')).toBeInTheDocument();
    expect(panel.getByText('4')).toBeInTheDocument();
  });

  it('draws the progress bar to the same figure', async () => {
    theBookHas([chapter('c1', 'completed', 100), chapter('c2', 'draft', 0), chapter('c3', 'draft', 0)]);

    const panel = await stats();

    expect(panel.getByText('33%')).toBeInTheDocument();
    expect(panel.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '33');
    expect(panel.getByRole('progressbar').firstElementChild).toHaveStyle({ width: '33%' });
  });

  it('never says undefined: a book with no chapters is at 0%', async () => {
    theBookHas([]);

    const panel = await stats();

    expect(panel.getByText('0%')).toBeInTheDocument();
    expect(panel.getByText('0 of 0')).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent('undefined');
    expect(document.body.innerHTML).not.toContain('undefined%');
  });

  it('nor when the chapters could not be read', async () => {
    mockedClient.getChaptersMetadata.mockRejectedValue(new Error('Network error'));

    const panel = await stats();

    expect(panel.getByText('0%')).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent('undefined');
    expect(document.body.innerHTML).not.toContain('undefined%');
  });

  it('still shows the chapter tabs for a book that has chapters', async () => {
    theBookHas([chapter('c1', 'draft', 0)]);

    await stats();

    expect(await screen.findByTestId('chapter-tabs')).toBeInTheDocument();
  });
});
