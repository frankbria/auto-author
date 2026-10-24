import React, { Suspense } from 'react';
import { act, render, screen, within } from '@testing-library/react';
import '@testing-library/jest-dom';

import BookPage from '../page';
import bookClient from '@/lib/api/bookClient';
import type { ChapterTabMetadata } from '@/types/chapter-tabs';

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
jest.mock('@/components/export/ExportOptionsModal', () => ({ ExportOptionsModal: () => null }));
jest.mock('@/components/export/ExportProgressModal', () => ({ ExportProgressModal: () => null }));

// The tabs own the live chapter list; the page hears about it through onChaptersChange (#1092).
let report: (chapters: ChapterTabMetadata[]) => void = () => {};
jest.mock('@/components/chapters/ChapterTabs', () => ({
  ChapterTabs: ({ onChaptersChange }: { onChaptersChange?: (c: ChapterTabMetadata[]) => void }) => {
    report = onChaptersChange ?? (() => {});
    return <div data-testid="chapter-tabs" />;
  },
}));

const mockedClient = bookClient as jest.Mocked<typeof bookClient>;
type Book = Awaited<ReturnType<typeof bookClient.getBook>>;
type Metadata = Awaited<ReturnType<typeof bookClient.getChaptersMetadata>>;

const value = { bookId: 'book-1' };
const params = Object.assign(Promise.resolve(value), { status: 'fulfilled', value }) as Promise<{ bookId: string }>;

const chapter = (id: string, status: string, word_count: number) =>
  ({ id, title: `Chapter ${id}`, order: 1, level: 1, status, word_count, last_modified: '', estimated_reading_time: 1, has_content: true }) as ChapterTabMetadata;

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
    { id: 'book-1', title: 'T', description: '', owner_id: 'u1', created_at: '', updated_at: '' } as unknown as Book,
  );
  mockedClient.getBookSummary.mockResolvedValue({ summary: 'A summary long enough to count as one.', summary_history: [] } as never);
  const chapters = [chapter('c1', 'draft', 100), chapter('c2', 'draft', 0)];
  mockedClient.getChaptersMetadata.mockResolvedValue({
    book_id: 'book-1', chapters, total_chapters: 2,
    completion_stats: { draft: 0, in_progress: 0, completed: 0, published: 0 },
  } as unknown as Metadata);
});

describe('the Book Stats panel follows the chapter tabs (#1092)', () => {
  it('counts a chapter a background TOC refresh added', async () => {
    const panel = await stats();
    expect(panel.getByText('0 of 2')).toBeInTheDocument();

    act(() => report([chapter('c1', 'draft', 100), chapter('c2', 'draft', 0), chapter('c3', 'draft', 40)]));

    expect(panel.getByText('0 of 3')).toBeInTheDocument();
    expect(panel.getByText('140')).toBeInTheDocument();
  });

  it('moves completed and progress when a chapter status changes in the tabs', async () => {
    const panel = await stats();

    act(() => report([chapter('c1', 'completed', 100), chapter('c2', 'draft', 0)]));

    expect(panel.getByText('1 of 2')).toBeInTheDocument();
    expect(panel.getByText('50%')).toBeInTheDocument();
    expect(panel.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '50');
  });
});
