import React, { Suspense } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import EditTOCPage from '../edit-toc/page';
import { useSession } from '@/lib/auth-client';
import bookClient from '@/lib/api/bookClient';

jest.mock('@/lib/auth-client');
jest.mock('@/lib/api/bookClient');
jest.mock('@/hooks/useTocSync', () => ({ triggerTocUpdateEvent: jest.fn() }));

const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;

// Pre-fulfilled thenable so React's use(params) reads synchronously (#194).
function fulfilledParams<T>(value: T): Promise<T> {
  const p = Promise.resolve(value) as Promise<T> & { status: string; value: T };
  p.status = 'fulfilled';
  p.value = value;
  return p;
}

// #861: the backend writes status "in-progress" once a chapter passes 100 words.
// The frontend enum used "in_progress", so the indicator threw and the error
// boundary replaced the whole page.
const tocWith = (chapters: unknown[], version?: number) =>
  ({ toc: { chapters, total_chapters: chapters.length, estimated_pages: 15, structure_notes: '' }, version }) as never;

const chapter = (id: string, title: string, order: number, status: string) => ({
  id, title, description: '', level: 1, order, status, word_count: 10, subchapters: [],
});

function renderPage() {
  return render(
    <Suspense fallback={null}>
      <EditTOCPage params={fulfilledParams({ bookId: 'book-1' })} />
    </Suspense>
  );
}

describe('Edit TOC page: chapter with backend status "in-progress" (#861)', () => {
  it('shows "In Progress" instead of crashing', async () => {
    (useSession as jest.Mock).mockReturnValue({ data: { user: { id: 'u1' } } });
    mockBookClient.getToc.mockResolvedValue({
      toc: {
        chapters: [
          {
            id: 'ch1',
            title: 'Drafted Chapter',
            description: 'has a real draft',
            level: 1,
            order: 1,
            status: 'in-progress',
            word_count: 250,
            subchapters: [],
          },
        ],
        total_chapters: 1,
        estimated_pages: 15,
        structure_notes: '',
      },
    } as never);

    render(
      <Suspense fallback={null}>
        <EditTOCPage params={fulfilledParams({ bookId: 'book-1' })} />
      </Suspense>
    );

    expect(await screen.findByDisplayValue('Drafted Chapter')).toBeInTheDocument();
    expect(screen.getByText('In Progress')).toBeInTheDocument();
  });
});

describe('Edit TOC page: editing a TOC that has in-progress chapters (#861)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useSession as jest.Mock).mockReturnValue({ data: { user: { id: 'u1' } } });
    mockBookClient.getToc.mockResolvedValue(
      tocWith([chapter('c1', 'One', 1, 'in-progress'), chapter('c2', 'Two', 2, 'draft')])
    );
    mockBookClient.updateToc.mockResolvedValue(undefined as never);
  });

  it('renames, adds, nests and deletes chapters, then saves the edited tree', async () => {
    renderPage();
    fireEvent.change(await screen.findByDisplayValue('One'), { target: { value: 'One renamed' } });
    fireEvent.change(screen.getAllByPlaceholderText('Chapter description (optional)')[0], {
      target: { value: 'about one' },
    });
    fireEvent.click(screen.getAllByTitle('Add Subchapter')[0]);
    fireEvent.click(screen.getByRole('button', { name: /add chapter/i }));
    fireEvent.click(screen.getAllByTitle('Delete Chapter')[2]); // One, its new subchapter, then Two
    expect(screen.getByDisplayValue('New Chapter')).toBeInTheDocument();
    expect(screen.queryByDisplayValue('Two')).not.toBeInTheDocument();
    expect(screen.getByText('In Progress')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /save & continue/i }));
    await waitFor(() => expect(mockBookClient.updateToc).toHaveBeenCalled());
    const saved = mockBookClient.updateToc.mock.calls[0][1] as { chapters: { title: string; subchapters: unknown[] }[] };
    expect(saved.chapters.map((c) => c.title)).toEqual(['One renamed', 'New Chapter']);
    expect(saved.chapters[0].subchapters).toHaveLength(1);
  });

  it('reorders by drag and drop', async () => {
    renderPage();
    const first = (await screen.findByDisplayValue('One')).closest('[draggable]') as HTMLElement;
    const second = screen.getByDisplayValue('Two').closest('[draggable]') as HTMLElement;
    fireEvent.dragStart(first);
    fireEvent.dragEnter(second);
    fireEvent.dragOver(second);
    fireEvent.dragLeave(second);
    fireEvent.dragEnter(second);
    fireEvent.drop(second);
    fireEvent.click(screen.getByRole('button', { name: /save & continue/i }));
    await waitFor(() => expect(mockBookClient.updateToc).toHaveBeenCalled());
    const saved = mockBookClient.updateToc.mock.calls[0][1] as { chapters: { title: string }[] };
    expect(saved.chapters.map((c) => c.title).sort()).toEqual(['One', 'Two']);
  });

  it('shows an error when the save fails', async () => {
    mockBookClient.updateToc.mockRejectedValue(new Error('boom'));
    jest.spyOn(console, 'error').mockImplementation(() => {});
    renderPage();
    await screen.findByDisplayValue('One');
    fireEvent.click(screen.getByRole('button', { name: /save & continue/i }));
    expect(await screen.findByText(/failed to save the table of contents/i)).toBeInTheDocument();
  });

  it('shows the empty state for a book with no TOC', async () => {
    mockBookClient.getToc.mockResolvedValue({ toc: null } as never);
    renderPage();
    expect(await screen.findByText(/no chapters yet/i)).toBeInTheDocument();
  });
});

describe('Edit TOC page: optimistic lock (#750)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useSession as jest.Mock).mockReturnValue({ data: { user: { id: 'u1' } } });
    mockBookClient.getToc.mockResolvedValue(tocWith([chapter('c1', 'One', 1, 'draft')], 4));
    mockBookClient.updateToc.mockResolvedValue(undefined as never);
  });

  it('sends the version read from GET /toc as expected_version', async () => {
    renderPage();
    await screen.findByDisplayValue('One');
    fireEvent.click(screen.getByRole('button', { name: /save & continue/i }));
    await waitFor(() => expect(mockBookClient.updateToc).toHaveBeenCalled());
    expect(mockBookClient.updateToc.mock.calls[0][1]).toEqual(expect.objectContaining({ expected_version: 4 }));
  });

  it('omits expected_version when no TOC exists yet (version 0)', async () => {
    mockBookClient.getToc.mockResolvedValue(tocWith([chapter('c1', 'One', 1, 'draft')], 0));
    renderPage();
    await screen.findByDisplayValue('One');
    fireEvent.click(screen.getByRole('button', { name: /save & continue/i }));
    await waitFor(() => expect(mockBookClient.updateToc).toHaveBeenCalled());
    expect(mockBookClient.updateToc.mock.calls[0][1]).not.toHaveProperty('expected_version');
  });

  it('on a 409 says the TOC changed elsewhere and Reload refetches the new version', async () => {
    jest.spyOn(console, 'error').mockImplementation(() => {});
    mockBookClient.updateToc.mockRejectedValue(Object.assign(new Error('modified by another user'), { statusCode: 409 }));
    renderPage();
    await screen.findByDisplayValue('One');
    fireEvent.change(screen.getByDisplayValue('One'), { target: { value: 'Mine' } });
    fireEvent.click(screen.getByRole('button', { name: /save & continue/i }));
    expect(await screen.findByText(/changed elsewhere/i)).toBeInTheDocument();
    expect(screen.queryByText(/failed to save the table of contents/i)).not.toBeInTheDocument();

    mockBookClient.getToc.mockResolvedValue(tocWith([chapter('c1', 'Theirs', 1, 'draft')], 5));
    fireEvent.click(screen.getByRole('button', { name: /reload/i }));
    expect(await screen.findByDisplayValue('Theirs')).toBeInTheDocument();
    expect(screen.queryByText(/changed elsewhere/i)).not.toBeInTheDocument();

    mockBookClient.updateToc.mockResolvedValue(undefined as never);
    fireEvent.click(screen.getByRole('button', { name: /save & continue/i }));
    await waitFor(() => expect(mockBookClient.updateToc).toHaveBeenCalledTimes(2));
    expect(mockBookClient.updateToc.mock.calls[1][1]).toEqual(expect.objectContaining({ expected_version: 5 }));
  });

  it('drops the Reload button when a later save fails for a non-conflict reason', async () => {
    jest.spyOn(console, 'error').mockImplementation(() => {});
    mockBookClient.updateToc.mockRejectedValueOnce(Object.assign(new Error('conflict'), { statusCode: 409 }));
    renderPage();
    await screen.findByDisplayValue('One');
    fireEvent.click(screen.getByRole('button', { name: /save & continue/i }));
    expect(await screen.findByRole('button', { name: /reload/i })).toBeInTheDocument();

    mockBookClient.updateToc.mockRejectedValueOnce(Object.assign(new Error('boom'), { statusCode: 500 }));
    fireEvent.click(screen.getByRole('button', { name: /save & continue/i }));
    expect(await screen.findByText(/failed to save the table of contents/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /reload/i })).not.toBeInTheDocument();
  });
});
