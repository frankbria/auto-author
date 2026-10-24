import { act, render, waitFor } from '@testing-library/react';
import { ChapterTabs } from '../ChapterTabs';
import { triggerTocUpdateEvent } from '@/hooks/useTocSync';
import bookClient from '@/lib/api/bookClient';

jest.mock('@/lib/api/bookClient');
const mockBookClient = bookClient as jest.Mocked<typeof bookClient>;

type Toc = Awaited<ReturnType<typeof bookClient.getToc>>;
const toc = (...ids: string[]): Toc =>
  ({
    toc: {
      chapters: ids.map((id, i) => ({ id, title: `Chapter ${id}`, description: '', level: 1, order: i + 1, subchapters: [] })),
      total_chapters: ids.length, estimated_pages: 1, structure_notes: '',
    },
  }) as unknown as Toc;

describe('ChapterTabs onChaptersChange (#1092)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    mockBookClient.getToc.mockResolvedValue(toc('A', 'B'));
    mockBookClient.getTabState.mockResolvedValue(null as never);
    mockBookClient.saveTabState.mockResolvedValue({} as never);
    mockBookClient.getChapterContent.mockImplementation(async (_b, id) => ({ content: '<p>x</p>', chapter_id: id, book_id: 'bk' }));
  });

  it('reports the loaded chapters, then the list a background TOC refresh produced', async () => {
    const onChaptersChange = jest.fn();
    render(<ChapterTabs bookId="bk" onChaptersChange={onChaptersChange} />);
    await waitFor(() => expect(onChaptersChange).toHaveBeenCalled());
    expect(onChaptersChange.mock.calls.at(-1)![0].map((c: { id: string }) => c.id)).toEqual(['A', 'B']);

    mockBookClient.getToc.mockResolvedValue(toc('A', 'B', 'C'));
    await act(async () => triggerTocUpdateEvent('bk'));

    await waitFor(() =>
      expect(onChaptersChange.mock.calls.at(-1)![0].map((c: { id: string }) => c.id)).toEqual(['A', 'B', 'C']),
    );
  });
});
